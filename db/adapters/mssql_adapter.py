from __future__ import annotations

import re
import time
import urllib.parse

from sqlalchemy import create_engine, text

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
        with self._engine.connect() as conn:
            # Tables
            rows = conn.execute(text(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
            )).fetchall()
            all_tables = [r[0] for r in rows]
            target = tables if tables else all_tables

            # Primary keys per table
            pk_rows = conn.execute(text(
                "SELECT ku.TABLE_NAME, ku.COLUMN_NAME "
                "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
                "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku "
                "  ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME "
                "  AND tc.TABLE_SCHEMA = ku.TABLE_SCHEMA "
                "WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'"
            )).fetchall()
            pk_map: dict[str, set[str]] = {}
            for tname, col in pk_rows:
                pk_map.setdefault(tname, set()).add(col)

            # Foreign keys per table
            fk_rows = conn.execute(text(
                "SELECT "
                "  fk.TABLE_NAME, fk.COLUMN_NAME, "
                "  pk.TABLE_NAME AS REF_TABLE, pk.COLUMN_NAME AS REF_COLUMN "
                "FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc "
                "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE fk "
                "  ON rc.CONSTRAINT_NAME = fk.CONSTRAINT_NAME "
                "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pk "
                "  ON rc.UNIQUE_CONSTRAINT_NAME = pk.CONSTRAINT_NAME "
                "  AND fk.ORDINAL_POSITION = pk.ORDINAL_POSITION"
            )).fetchall()
            fk_map: dict[str, list[dict]] = {}
            for tname, col, ref_table, ref_col in fk_rows:
                fk_map.setdefault(tname, []).append({
                    "columns": [col],
                    "references": f"{ref_table}.{ref_col}",
                })

            # Columns per table
            col_rows = conn.execute(text(
                "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "ORDER BY TABLE_NAME, ORDINAL_POSITION"
            )).fetchall()
            col_map: dict[str, list[ColumnInfo]] = {}
            for tname, cname, dtype, nullable in col_rows:
                col_map.setdefault(tname, []).append(
                    ColumnInfo(
                        name=cname,
                        type=dtype,
                        nullable=(nullable == "YES"),
                        primary_key=(cname in pk_map.get(tname, set())),
                    )
                )

        schema: list[TableInfo] = []
        for table_name in target:
            if table_name not in all_tables:
                continue
            schema.append(
                TableInfo(
                    name=table_name,
                    columns=col_map.get(table_name, []),
                    foreign_keys=fk_map.get(table_name, []),
                )
            )
        return schema
