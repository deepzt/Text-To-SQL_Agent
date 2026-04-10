from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import create_engine, inspect, text


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_ms: float
    error: str | None = None


@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    primary_key: bool


@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[dict] = field(default_factory=list)
    sample_values: dict[str, list] = field(default_factory=dict)


class SQLiteAdapter:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, echo=False)

    def test_connection(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def execute(self, sql: str, limit: int = 100) -> QueryResult:
        start = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                # Inject LIMIT if not already present and it's a SELECT
                normalized = sql.strip().upper()
                if normalized.startswith("SELECT") and "LIMIT" not in normalized:
                    sql = f"{sql.rstrip(';')} LIMIT {limit}"
                result = conn.execute(text(sql))
                columns = list(result.keys())
                rows = [list(row) for row in result.fetchall()]
                elapsed = (time.perf_counter() - start) * 1000
                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_ms=round(elapsed, 2),
                )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                execution_ms=round(elapsed, 2),
                error=str(exc),
            )

    def get_schema(self, tables: list[str] | None = None) -> list[TableInfo]:
        inspector = inspect(self._engine)
        all_tables = inspector.get_table_names()
        target = tables if tables else all_tables

        schema: list[TableInfo] = []
        pk_sets: dict[str, set] = {}

        for table_name in target:
            if table_name not in all_tables:
                continue

            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols: set[str] = set(pk_constraint.get("constrained_columns", []))
            pk_sets[table_name] = pk_cols

            columns_raw = inspector.get_columns(table_name)
            columns = [
                ColumnInfo(
                    name=col["name"],
                    type=str(col["type"]),
                    nullable=col.get("nullable", True),
                    primary_key=col["name"] in pk_cols,
                )
                for col in columns_raw
            ]

            fk_raw = inspector.get_foreign_keys(table_name)
            foreign_keys = [
                {
                    "columns": fk["constrained_columns"],
                    "references": f"{fk['referred_table']}.{fk['referred_columns']}",
                }
                for fk in fk_raw
            ]

            # Sample up to 3 distinct values for text/varchar columns (for enum-like hints)
            sample_values: dict[str, list] = {}
            text_cols = [c.name for c in columns if "CHAR" in c.type.upper() or "TEXT" in c.type.upper()]
            if text_cols:
                with self._engine.connect() as conn:
                    for col in text_cols[:5]:  # limit to 5 cols to keep schema compact
                        try:
                            result = conn.execute(
                                text(f'SELECT DISTINCT "{col}" FROM "{table_name}" LIMIT 3')
                            )
                            vals = [row[0] for row in result if row[0] is not None]
                            if vals:
                                sample_values[col] = vals
                        except Exception:
                            pass

            schema.append(
                TableInfo(
                    name=table_name,
                    columns=columns,
                    foreign_keys=foreign_keys,
                    sample_values=sample_values,
                )
            )

        return schema
