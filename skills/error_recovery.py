"""
Skill: error_recovery
Claude tool name: recover_from_error

When execute_sql or validate_sql returns an error, this skill calls the LLM
provider to diagnose the failure and produce a corrected SQL query.
Max 3 recovery attempts before giving up.
"""

from __future__ import annotations

# ── Tool definition ───────────────────────────────────────────────────────────

TOOL_DEFINITION = {
    "name": "recover_from_error",
    "description": (
        "Diagnose and fix a SQL query that failed validation or execution. "
        "Provide the original SQL, the error message, and which attempt this is (1-3). "
        "After 3 failed attempts the agent will explain why the query cannot be answered."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "failing_sql": {
                "type": "string",
                "description": "The SQL that failed.",
            },
            "error_message": {
                "type": "string",
                "description": "The exact error or validation message.",
            },
            "attempt_number": {
                "type": "integer",
                "description": "Which retry attempt this is (1, 2, or 3).",
            },
        },
        "required": ["failing_sql", "error_message", "attempt_number"],
    },
}

# ── Skill function ────────────────────────────────────────────────────────────

def recover_from_error(
    provider,
    schema_text: str,
    failing_sql: str,
    error_message: str,
    attempt_number: int,
    max_attempts: int = 3,
) -> dict:
    """
    Call the LLM provider to diagnose and fix a failing SQL query.

    Args:
        provider: An LLMProvider instance.
        schema_text: Text representation of the DB schema.
        failing_sql: The SQL that produced an error.
        error_message: The error or validation message.
        attempt_number: Which retry attempt (1-indexed).
        max_attempts: Stop retrying after this many attempts.

    Returns:
        {
            "corrected_sql": str | None,
            "diagnosis": str,
            "give_up": bool
        }
    """
    if attempt_number > max_attempts:
        return {
            "corrected_sql": None,
            "diagnosis": (
                f"Reached maximum recovery attempts ({max_attempts}). "
                "Unable to automatically fix this query."
            ),
            "give_up": True,
        }

    system_prompt = (
        "You are an expert SQL debugger. "
        "Given a failing SQL query, an error message, and the database schema, "
        "diagnose the problem and produce a corrected SQL query. "
        "Respond ONLY with a JSON object with keys: "
        '"corrected_sql" (string, the fixed SQL) and '
        '"diagnosis" (string, brief explanation of what was wrong). '
        "If the query is fundamentally unanswerable given the schema, "
        'set "corrected_sql" to null and explain in "diagnosis".\n\n'
        f"{schema_text}"
    )

    user_message = (
        f"Failing SQL:\n```sql\n{failing_sql}\n```\n\n"
        f"Error message:\n{error_message}\n\n"
        f"This is attempt {attempt_number} of {max_attempts}. "
        "Please provide a corrected SQL query."
    )

    response = provider.chat(
        messages=[{"role": "user", "content": user_message}],
        tools=[],
        system=system_prompt,
        max_tokens=4096,
    )

    import json, re

    text = response.content_text.strip()
    # Try to extract JSON from the response
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return {
                "corrected_sql": data.get("corrected_sql"),
                "diagnosis": data.get("diagnosis", ""),
                "give_up": data.get("corrected_sql") is None,
            }
        except json.JSONDecodeError:
            pass

    # Fallback: return the raw text as diagnosis
    return {
        "corrected_sql": None,
        "diagnosis": text,
        "give_up": True,
    }
