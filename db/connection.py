from __future__ import annotations

from .adapters.sqlite_adapter import SQLiteAdapter, QueryResult, TableInfo
from .adapters.postgres_adapter import PostgresAdapter
from .adapters.mysql_adapter import MySQLAdapter
from .adapters.mssql_adapter import MSSQLAdapter


def get_connection(database_url: str):
    """Return the correct DB adapter based on the DATABASE_URL scheme."""
    url = database_url.strip().lower()
    if url.startswith("sqlite"):
        return SQLiteAdapter(database_url)
    elif url.startswith("postgresql") or url.startswith("postgres"):
        return PostgresAdapter(database_url)
    elif url.startswith("mysql"):
        return MySQLAdapter(database_url)
    elif url.startswith("mssql") or url.startswith("driver="):
        return MSSQLAdapter(database_url)
    else:
        raise ValueError(f"Unsupported database URL scheme: {database_url}")


__all__ = ["get_connection", "QueryResult", "TableInfo"]
