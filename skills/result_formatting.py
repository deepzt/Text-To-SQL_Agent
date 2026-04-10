"""
Skill: result_formatting
Claude tool name: format_results

Converts raw query results (columns + rows) into human-readable output.
Auto-detects result shape and picks the best format.
"""

from __future__ import annotations

from typing import Any

# ── Tool definition ───────────────────────────────────────────────────────────

TOOL_DEFINITION = {
    "name": "format_results",
    "description": (
        "Format raw SQL query results into a human-readable presentation. "
        "Automatically chooses the best format based on result shape "
        "(single value, list, or full table). "
        "Call this as the last step before returning the answer to the user."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Column names from the query result.",
            },
            "rows": {
                "type": "array",
                "description": "List of rows (each row is a list of values).",
            },
            "row_count": {
                "type": "integer",
                "description": "Total number of rows returned.",
            },
            "format": {
                "type": "string",
                "enum": ["auto", "markdown_table", "plain_text", "json", "csv"],
                "description": "Output format. 'auto' picks the best fit.",
                "default": "auto",
            },
            "include_summary": {
                "type": "boolean",
                "description": "Prepend a one-sentence plain-English summary.",
                "default": True,
            },
        },
        "required": ["columns", "rows", "row_count"],
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _markdown_table(columns: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_No results._"
    col_widths = [
        max(len(str(col)), max((len(str(r[i])) for r in rows), default=0))
        for i, col in enumerate(columns)
    ]
    header = " | ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(columns))
    separator = "-|-".join("-" * w for w in col_widths)
    body_lines = [
        " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        for row in rows
    ]
    return "\n".join([header, separator] + body_lines)


def _plain_summary(columns: list[str], rows: list[list[Any]], row_count: int) -> str:
    if row_count == 0:
        return "No results found."
    if len(columns) == 1 and row_count == 1:
        return f"Result: {rows[0][0]}"
    if len(columns) == 1:
        vals = ", ".join(str(r[0]) for r in rows[:5])
        suffix = f"... (+{row_count - 5} more)" if row_count > 5 else ""
        return f"{columns[0]}: {vals}{suffix}"
    return f"Found {row_count} row(s) across {len(columns)} column(s)."


# ── Skill function ────────────────────────────────────────────────────────────

def format_results(
    columns: list[str],
    rows: list[list[Any]],
    row_count: int,
    format: str = "auto",
    include_summary: bool = True,
) -> dict:
    """
    Format query results and return a dict with 'formatted' and 'summary' keys.
    """
    if format == "auto":
        if row_count == 0:
            format = "plain_text"
        elif len(columns) == 1 and row_count == 1:
            format = "plain_text"
        else:
            format = "markdown_table"

    if format == "markdown_table":
        formatted = _markdown_table(columns, rows)
    elif format == "plain_text":
        formatted = _plain_summary(columns, rows, row_count)
    elif format == "json":
        import json
        formatted = json.dumps(
            [dict(zip(columns, row)) for row in rows], indent=2, default=str
        )
    elif format == "csv":
        lines = [",".join(columns)]
        for row in rows:
            lines.append(",".join(f'"{str(v)}"' for v in row))
        formatted = "\n".join(lines)
    else:
        formatted = str(rows)

    summary = _plain_summary(columns, rows, row_count) if include_summary else ""

    return {
        "formatted": formatted,
        "summary": summary,
        "format_used": format,
        "row_count": row_count,
    }
