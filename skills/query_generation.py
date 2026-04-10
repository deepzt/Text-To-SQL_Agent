"""
Skill: query_generation
Claude tool name: submit_sql_query

Structured handoff point: Claude calls this tool to commit to a generated SQL
query. The tool validates syntax via sqlglot and returns the result.

The actual SQL generation happens in Claude's reasoning — this tool acts as a
structured commit gate with explicit confidence and explanation.
"""

from __future__ import annotations

import sqlglot

# ── Tool definition ───────────────────────────────────────────────────────────

TOOL_DEFINITION = {
    "name": "submit_sql_query",
    "description": (
        "Submit the SQL query you have generated based on the user's question and the schema. "
        "Use this after you have determined the correct SQL. "
        "Include a plain-English explanation and your confidence level. "
        "Low-confidence queries will be routed through extra validation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "The complete SQL SELECT query to execute.",
            },
            "explanation": {
                "type": "string",
                "description": "Plain-English explanation of what this SQL does.",
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Your confidence that this query is correct.",
            },
        },
        "required": ["sql", "explanation", "confidence"],
    },
}

# ── Skill function ────────────────────────────────────────────────────────────

def submit_sql_query(
    sql: str,
    explanation: str,
    confidence: str,
    dialect: str = "sqlite",
) -> dict:
    """
    Syntax-check the SQL via sqlglot and return a structured result.

    Returns:
        dict with keys: sql, explanation, confidence, syntax_valid, syntax_error
    """
    syntax_error: str | None = None
    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
        if not parsed:
            syntax_error = "Could not parse SQL — empty parse result."
    except sqlglot.errors.ParseError as exc:
        syntax_error = str(exc)

    return {
        "sql": sql,
        "explanation": explanation,
        "confidence": confidence,
        "syntax_valid": syntax_error is None,
        "syntax_error": syntax_error,
    }
