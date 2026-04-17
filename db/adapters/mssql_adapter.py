from __future__ import annotations

import re
import time
import urllib.parse

from sqlalchemy import create_engine, inspect, text

from .sqlite_adapter import ColumnInfo, QueryResult, TableInfo


class MSSQLAdapter:
    def __init__(self, database_url: str) -> None:
        if database_url.strip().upper().startswith("DRIVER="):
            database_url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(database_url)
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
                normalized = sql.strip().upper()
                # SQL Server uses TOP instead of LIMIT
                if normalized.startswith("SELECT") and not re.search(r"\bTOP\b", normalized):
                    sql = re.sub(r"(?i)^(SELECT)", f"SELECT TOP {limit}", sql.strip(), count=1)
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
        # SQL Server organises tables under schemas; default to 'dbo'
        all_tables = inspector.get_table_names(schema="dbo")
        target = tables if tables else all_tables

        schema: list[TableInfo] = []
        for table_name in target:
            if table_name not in all_tables:
                continue
            pk_constraint = inspector.get_pk_constraint(table_name, schema="dbo")
            pk_cols: set[str] = set(pk_constraint.get("constrained_columns", []))
            columns_raw = inspector.get_columns(table_name, schema="dbo")
            columns = [
                ColumnInfo(
                    name=col["name"],
                    type=str(col["type"]),
                    nullable=col.get("nullable", True),
                    primary_key=col["name"] in pk_cols,
                )
                for col in columns_raw
            ]
            fk_raw = inspector.get_foreign_keys(table_name, schema="dbo")
            foreign_keys = [
                {
                    "columns": fk["constrained_columns"],
                    "references": f"{fk['referred_table']}.{fk['referred_columns']}",
                }
                for fk in fk_raw
            ]
            schema.append(
                TableInfo(
                    name=table_name,
                    columns=columns,
                    foreign_keys=foreign_keys,
                )
            )
        return schema
