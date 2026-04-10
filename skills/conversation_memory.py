"""
Skill: conversation_memory
Claude tool name: recall_context

In-memory store for multi-turn session state:
  - DB schema (to avoid re-fetching)
  - Previously executed queries and their results
  - User preferences
"""

from __future__ import annotations

from typing import Any

# ── Tool definition ───────────────────────────────────────────────────────────

TOOL_DEFINITION = {
    "name": "recall_context",
    "description": (
        "Retrieve context from earlier in this conversation: "
        "previously mentioned table names, column names, query results, or user preferences. "
        "Use this to resolve references like 'those results', 'that table', "
        "'the previous query', etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": ["schema", "previous_query", "previous_results", "user_preferences", "all"],
                "description": "What type of context to retrieve.",
            }
        },
        "required": ["query_type"],
    },
}

# ── Memory store ──────────────────────────────────────────────────────────────

class ConversationMemory:
    """Single-session in-memory context store."""

    def __init__(self) -> None:
        self._schema: dict | None = None
        self._query_history: list[dict] = []   # [{sql, explanation, results, turn}]
        self._preferences: dict[str, Any] = {}

    # ── Writers ──────────────────────────────────────────────────────────────

    def set_schema(self, schema: dict) -> None:
        self._schema = schema

    def record_query(self, sql: str, explanation: str, results: dict, turn: int) -> None:
        self._query_history.append(
            {
                "turn": turn,
                "sql": sql,
                "explanation": explanation,
                "results": results,
            }
        )

    def set_preference(self, key: str, value: Any) -> None:
        self._preferences[key] = value

    # ── Reader (skill function) ───────────────────────────────────────────────

    def recall_context(self, query_type: str) -> dict:
        if query_type == "schema":
            return {"schema": self._schema}
        elif query_type == "previous_query":
            if self._query_history:
                last = self._query_history[-1]
                return {"sql": last["sql"], "explanation": last["explanation"], "turn": last["turn"]}
            return {"message": "No previous queries in this session."}
        elif query_type == "previous_results":
            if self._query_history:
                last = self._query_history[-1]
                return {
                    "results": last["results"],
                    "sql": last["sql"],
                    "turn": last["turn"],
                }
            return {"message": "No previous results in this session."}
        elif query_type == "user_preferences":
            return {"preferences": self._preferences}
        elif query_type == "all":
            return {
                "schema": self._schema,
                "query_history": self._query_history[-5:],  # last 5
                "preferences": self._preferences,
            }
        return {"error": f"Unknown query_type: {query_type}"}
