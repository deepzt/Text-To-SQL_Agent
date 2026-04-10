"""
Skill: schema_introspection
Claude tool name: get_schema

Reads table/column/FK info from the DB and returns a compact JSON schema.
Results are cached in-memory; pass refresh=True to force a re-fetch.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from db.adapters.sqlite_adapter import TableInfo

# ── Tool definition (passed to Claude/Ollama) ────────────────────────────────

TOOL_DEFINITION = {
    "name": "get_schema",
    "description": (
        "Retrieve the database schema including all tables, columns, data types, "
        "primary keys, foreign keys, and sample values for text columns. "
        "Call this before generating SQL if you don't already have the schema in context. "
        "Pass specific table names to limit the response."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tables": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional list of table names to introspect. "
                    "If omitted or empty, all tables are returned."
                ),
            },
            "refresh": {
                "type": "boolean",
                "description": "Force re-fetch even if schema is already cached.",
                "default": False,
            },
        },
        "required": [],
    },
}

# ── Cache ────────────────────────────────────────────────────────────────────

_SCHEMA_CACHE: list[TableInfo] | None = None


# ── Skill function ────────────────────────────────────────────────────────────

def get_schema(db, tables: list[str] | None = None, refresh: bool = False) -> dict:
    """
    Args:
        db: A DB adapter (SQLiteAdapter / PostgresAdapter / MySQLAdapter).
        tables: Optional list of table names to include.
        refresh: Force re-fetch from DB.

    Returns:
        dict with "schema" key containing list of table dicts,
        or "error" key on failure.
    """
    global _SCHEMA_CACHE

    if _SCHEMA_CACHE is None or refresh:
        _SCHEMA_CACHE = db.get_schema(tables if tables else None)

    target = _SCHEMA_CACHE
    if tables:
        target = [t for t in _SCHEMA_CACHE if t.name in tables]

    schema_list = []
    for table in target:
        t_dict = {
            "table": table.name,
            "columns": [
                {
                    "name": c.name,
                    "type": c.type,
                    "nullable": c.nullable,
                    "primary_key": c.primary_key,
                }
                for c in table.columns
            ],
        }
        if table.foreign_keys:
            t_dict["foreign_keys"] = table.foreign_keys
        if table.sample_values:
            t_dict["sample_values"] = table.sample_values
        schema_list.append(t_dict)

    return {"schema": schema_list, "table_count": len(schema_list)}


def schema_to_text(db) -> str:
    """Return a compact text representation of the full schema for system prompts."""
    result = get_schema(db)
    lines: list[str] = ["DATABASE SCHEMA:"]
    for t in result["schema"]:
        lines.append(f"\nTable: {t['table']}")
        for col in t["columns"]:
            flags = []
            if col["primary_key"]:
                flags.append("PK")
            if not col["nullable"]:
                flags.append("NOT NULL")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            lines.append(f"  - {col['name']} ({col['type']}){flag_str}")
        if t.get("foreign_keys"):
            for fk in t["foreign_keys"]:
                lines.append(f"  FK: {fk['columns']} → {fk['references']}")
        if t.get("sample_values"):
            for col, vals in t["sample_values"].items():
                lines.append(f"  Samples [{col}]: {vals}")
    return "\n".join(lines)
