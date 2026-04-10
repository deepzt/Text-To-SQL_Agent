"""Tests for skills/query_validation.py"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from skills.query_validation import validate_sql


def test_valid_select():
    result = validate_sql("SELECT id, name FROM users WHERE id = 1")
    assert result["valid"] is True
    assert result["severity"] == "ok"


def test_blocks_drop():
    result = validate_sql("DROP TABLE users", allow_write=False)
    assert result["valid"] is False
    assert any("Write queries" in issue for issue in result["issues"])


def test_blocks_delete():
    result = validate_sql("DELETE FROM users WHERE id = 1", allow_write=False)
    assert result["valid"] is False


def test_allows_write_when_enabled():
    result = validate_sql("INSERT INTO users (name) VALUES ('Alice')", allow_write=True)
    # Should pass write check (may still have other issues)
    assert not any("Write queries" in issue for issue in result["issues"])


def test_unknown_table():
    result = validate_sql(
        "SELECT * FROM nonexistent_table",
        known_tables=["users", "orders"]
    )
    assert any("nonexistent_table" in issue for issue in result["issues"])


def test_syntax_error():
    result = validate_sql("SELEKT * FRUM users")
    assert result["severity"] == "error"
    assert not result["valid"]
