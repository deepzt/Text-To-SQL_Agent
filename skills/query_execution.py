"""
Skill: query_execution
Claude tool name: execute_sql

Runs a validated SQL query against the configured database.
Enforces a hard row LIMIT and records execution time.
"""

from __future__ import annotations

# ── Tool definition ───────────────────────────────────────────────────────────

TOOL_DEFINITION = {
    "name": "execute_sql",
    "description": (
        "Execute a SQL query against the database. "
        "Only call this after validate_sql returns no errors (or directly after "
        "submit_sql_query with high confidence). "
        "Returns columns, rows, row count, and execution time."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "The SQL query to execute.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum rows to return (default 100).",
                "default": 100,
            },
        },
        "required": ["sql"],
    },
}

# ── Skill function ────────────────────────────────────────────────────────────

def execute_sql(db, sql: str, limit: int = 100) -> dict:
    """
    Execute a SQL query via the DB adapter.

    Returns:
        On success: {columns, rows, row_count, execution_ms}
        On error:   {error, execution_ms}
    """
    result = db.execute(sql, limit=limit)

    if result.error:
        return {
            "error": result.error,
            "execution_ms": result.execution_ms,
        }

    return {
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "execution_ms": result.execution_ms,
    }
