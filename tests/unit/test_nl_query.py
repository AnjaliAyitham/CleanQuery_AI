import pytest
from app.services.nl_query import validate_sql


class TestValidateSQL:
    def test_valid_select(self):
        assert validate_sql("SELECT * FROM users") is True

    def test_valid_with_cte(self):
        assert validate_sql("WITH cte AS (SELECT 1) SELECT * FROM cte") is True

    def test_rejects_insert(self):
        assert validate_sql("INSERT INTO users VALUES (1, 'a')") is False

    def test_rejects_delete(self):
        assert validate_sql("DELETE FROM users WHERE id = 1") is False

    def test_rejects_drop(self):
        assert validate_sql("DROP TABLE users") is False

    def test_rejects_update(self):
        assert validate_sql("UPDATE users SET name = 'x'") is False

    def test_rejects_alter(self):
        assert validate_sql("ALTER TABLE users ADD COLUMN x INT") is False

    def test_rejects_truncate(self):
        assert validate_sql("TRUNCATE TABLE users") is False
