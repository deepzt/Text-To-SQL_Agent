"""
Core agentic loop — TextToSQLAgent.

Orchestrates the 7 skills via the chosen LLM provider (Claude or Ollama).
Claude decides which tools to call and in what order; the agent loop executes
each tool and feeds results back until Claude produces a final answer.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from config import Config
from db.connection import get_connection
from providers import get_provider
from skills import ALL_TOOLS
from skills.schema_introspection import get_schema, schema_to_text
from skills.query_generation import submit_sql_query
from skills.query_validation import validate_sql
from skills.query_execution import execute_sql
from skills.result_formatting import format_results
from skills.error_recovery import recover_from_error
from skills.conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)


class TextToSQLAgent:
    def __init__(self) -> None:
        db_target = Config.MSSQL_CONNECTION_STRING or Config.DATABASE_URL
        self._db = get_connection(db_target)
        self._provider = get_provider(Config)
        self._memory = ConversationMemory()
        self._turn = 0
        self._error_attempts: dict[str, int] = {}  # sql -> attempt count

        if not self._db.test_connection():
            raise RuntimeError(f"Cannot connect to database: {db_target}")

        logger.info(
            "TextToSQLAgent ready | provider=%s | db=%s",
            Config.LLM_PROVIDER,
            db_target,
        )

    # ── System prompt ─────────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        schema_text = schema_to_text(self._db)
        return (
            "You are an expert SQL assistant. "
            "Your job is to convert natural language questions into accurate SQL queries "
            "and return the results in a clear, human-readable format.\n\n"
            "Rules:\n"
            "1. The full database schema is already provided below — do NOT call get_schema "
            "   unless the user explicitly asks to refresh the schema.\n"
            "2. Use submit_sql_query to hand off your generated SQL — never execute SQL directly.\n"
            "3. Call validate_sql only for complex or uncertain queries.\n"
            "4. Always call format_results as the final step before answering.\n"
            "5. If execute_sql returns an error, call recover_from_error immediately.\n"
            "6. Only generate SELECT queries unless the user explicitly requests writes "
            "   AND write mode is enabled.\n"
            "7. Use recall_context to reference previous queries in multi-turn conversations.\n"
            "8. Be concise. Answer directly — do not over-explain.\n\n"
            f"{schema_text}"
        )

    # ── Tool dispatcher ───────────────────────────────────────────────────────

    def _execute_tool(
        self,
        name: str,
        tool_input: dict[str, Any],
        on_status: Callable[[str], None] | None = None,
    ) -> dict:
        logger.debug("Tool call: %s | input: %s", name, json.dumps(tool_input)[:200])

        _status_labels = {
            "get_schema": "Reading database schema...",
            "submit_sql_query": "Generating SQL query...",
            "validate_sql": "Validating query...",
            "execute_sql": "Executing query...",
            "format_results": "Formatting results...",
            "recover_from_error": "Recovering from error...",
            "recall_context": "Checking conversation history...",
        }
        if on_status and name in _status_labels:
            on_status(_status_labels[name])

        if name == "get_schema":
            return get_schema(
                self._db,
                tables=tool_input.get("tables"),
                refresh=tool_input.get("refresh", False),
            )

        elif name == "submit_sql_query":
            return submit_sql_query(
                sql=tool_input["sql"],
                explanation=tool_input["explanation"],
                confidence=tool_input["confidence"],
            )

        elif name == "validate_sql":
            schema_result = get_schema(self._db)
            known_tables = [t["table"] for t in schema_result.get("schema", [])]
            return validate_sql(
                sql=tool_input["sql"],
                dialect=tool_input.get("dialect", "sqlite"),
                allow_write=Config.ALLOW_WRITE_QUERIES,
                known_tables=known_tables,
            )

        elif name == "execute_sql":
            return execute_sql(
                db=self._db,
                sql=tool_input["sql"],
                limit=tool_input.get("limit", Config.MAX_ROWS_RETURNED),
            )

        elif name == "format_results":
            return format_results(
                columns=tool_input["columns"],
                rows=tool_input["rows"],
                row_count=tool_input["row_count"],
                format=tool_input.get("format", "auto"),
                include_summary=tool_input.get("include_summary", True),
            )

        elif name == "recover_from_error":
            failing_sql = tool_input["failing_sql"]
            attempt = tool_input["attempt_number"]
            key = failing_sql[:100]
            self._error_attempts[key] = self._error_attempts.get(key, 0) + 1
            return recover_from_error(
                provider=self._provider,
                schema_text=schema_to_text(self._db),
                failing_sql=failing_sql,
                error_message=tool_input["error_message"],
                attempt_number=attempt,
                max_attempts=Config.MAX_ERROR_RECOVERY_ATTEMPTS,
            )

        elif name == "recall_context":
            return self._memory.recall_context(tool_input["query_type"])

        else:
            return {"error": f"Unknown tool: {name}"}

    # ── Main agentic loop ─────────────────────────────────────────────────────

    def run(
        self,
        user_query: str,
        conversation_history: list[dict] | None = None,
        on_status: Callable[[str], None] | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        self._turn += 1
        messages: list[dict] = list(conversation_history or [])
        messages.append({"role": "user", "content": user_query})

        system = self._build_system_prompt()
        final_text = ""

        for iteration in range(20):  # safety cap on loop iterations
            if on_status:
                on_status("Thinking...")
            response = self._provider.chat(
                messages=messages,
                tools=ALL_TOOLS,
                system=system,
                max_tokens=4096,
                on_token=on_token,
            )

            if response.stop_reason == "end_turn" and not response.tool_uses:
                final_text = response.content_text
                break

            # Build the assistant message content
            assistant_content: list[dict] = []
            if response.content_text:
                assistant_content.append({"type": "text", "text": response.content_text})
            for tu in response.tool_uses:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tu.id,
                    "name": tu.name,
                    "input": tu.input,
                })
            messages.append({"role": "assistant", "content": assistant_content})

            if not response.tool_uses:
                # No tool calls but stop reason isn't end_turn — treat as final
                final_text = response.content_text
                break

            # Execute all tool calls and collect results
            tool_results: list[dict] = []
            for tu in response.tool_uses:
                result = self._execute_tool(tu.name, tu.input, on_status=on_status)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result, default=str),
                })
                logger.debug("Tool result: %s | %s", tu.name, json.dumps(result, default=str)[:200])

            messages.append({"role": "user", "content": tool_results})

        if not final_text:
            final_text = "I was unable to answer that query. Please try rephrasing."

        return final_text
