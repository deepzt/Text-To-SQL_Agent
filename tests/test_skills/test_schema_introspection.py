"""Tests for skills/schema_introspection.py"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from db.adapters.sqlite_adapter import SQLiteAdapter
from skills.schema_introspection import get_schema, schema_to_text


@pytest.fixture
def db(tmp_path):
    from sqlalchemy import create_engine, text
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT)"
        ))
        conn.execute(text(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, total REAL, "
            "FOREIGN KEY (user_id) REFERENCES users(id))"
        ))
    adapter = SQLiteAdapter(f"sqlite:///{db_path}")
    return adapter


def test_get_schema_returns_all_tables(db):
    result = get_schema(db, refresh=True)
    assert result["table_count"] == 2
    table_names = [t["table"] for t in result["schema"]]
    assert "users" in table_names
    assert "orders" in table_names


def test_get_schema_columns(db):
    result = get_schema(db, refresh=True)
    users = next(t for t in result["schema"] if t["table"] == "users")
    col_names = [c["name"] for c in users["columns"]]
    assert "id" in col_names
    assert "name" in col_names
    assert "email" in col_names


def test_get_schema_primary_key(db):
    result = get_schema(db, refresh=True)
    users = next(t for t in result["schema"] if t["table"] == "users")
    id_col = next(c for c in users["columns"] if c["name"] == "id")
    assert id_col["primary_key"] is True


def test_schema_to_text(db):
    text = schema_to_text(db)
    assert "users" in text
    assert "orders" in text
    assert "DATABASE SCHEMA" in text
