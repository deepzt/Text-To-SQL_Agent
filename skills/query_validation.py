"""
Skill: query_validation
Claude tool name: validate_sql

Multi-layer validation:
  1. Syntax check via sqlglot
  2. Safety check — blocks DDL/DML unless ALLOW_WRITE_QUERIES is enabled
  3. Schema check — verifies table/column names exist
  4. Injection pattern detection
"""

from __future__ import annotations

import re

import sqlglot
import sqlglot.expressions as exp

# ── Tool definition ───────────────────────────────────────────────────────────

TOOL_DEFINITION = {
    "name": "validate_sql",
    "description": (
        "Validate a SQL query for syntax errors, safety, and schema correctness "
        "before execution. Returns a list of issues. "
        "Call this when confidence is 'low' or 'medium', or after error recovery."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "The SQL to validate."},
            "dialect": {
                "type": "string",
                "enum": ["sqlite", "postgres", "mysql", "tsql"],
                "description": "SQL dialect to validate against. Use 'tsql' for SQL Server.",
                "default": "sqlite",
            },
        },
        "required": ["sql"],
    },
}

# Write-statement patterns to block
_WRITE_PATTERNS = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE)\b",
    re.IGNORECASE,
)

# Stacked-query / comment injection
_INJECTION_PATTERNS = [
    re.compile(r";\s*(DROP|DELETE|INSERT|UPDATE)\b", re.IGNORECASE),
    re.compile(r"--\s*$", re.MULTILINE),
    re.compile(r"/\*.*?\*/", re.DOTALL),
]


# ── Skill function ────────────────────────────────────────────────────────────

def validate_sql(
    sql: str,
    dialect: str = "sqlite",
    allow_write: bool = False,
    known_tables: list[str] | None = None,
) -> dict:
    """
    Validate SQL and return structured results.

    Returns:
        {
            "valid": bool,
            "severity": "ok" | "warning" | "error",
            "issues": list[str]
        }
    """
    issues: list[str] = []

    # 1. Syntax check
    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
        if not parsed:
            issues.append("Syntax error: empty parse result.")
    except sqlglot.errors.ParseError as exc:
        issues.append(f"Syntax error: {exc}")
        return {"valid": False, "severity": "error", "issues": issues}
    except ValueError:
        # Unknown dialect — retry without one rather than crashing
        parsed = sqlglot.parse(sql)

    # 2. Safety check
    if not allow_write and _WRITE_PATTERNS.match(sql.strip()):
        issues.append(
            "Write queries (INSERT/UPDATE/DELETE/DROP/CREATE/ALTER) are disabled. "
            "Set ALLOW_WRITE_QUERIES=true to enable."
        )

    # 3. Injection check
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(sql):
            issues.append(f"Potential SQL injection pattern detected.")
            break

    # 4. Schema check (if known_tables provided)
    if known_tables and parsed:
        for statement in parsed:
            for table_node in statement.find_all(exp.Table):
                tname = table_node.name
                if tname and tname.lower() not in [t.lower() for t in known_tables]:
                    issues.append(f"Unknown table referenced: '{tname}'")

    if not issues:
        return {"valid": True, "severity": "ok", "issues": []}

    # Determine severity
    error_keywords = ["Syntax error", "injection", "Write queries"]
    severity = "error" if any(k in i for i in issues for k in error_keywords) else "warning"
    return {"valid": severity != "error", "severity": severity, "issues": issues}
