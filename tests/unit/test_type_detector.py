import pytest
from app.utils.type_detector import detect_column_type, detect_date_format


class TestDetectColumnType:
    def test_integer_column(self):
        values = ["1", "2", "3", "100", "999"]
        assert detect_column_type(values) == "integer"

    def test_float_column(self):
        values = ["1.5", "2.7", "3.14", "100.0"]
        assert detect_column_type(values) == "float"

    def test_date_column(self):
        values = ["2024-01-01", "2024-02-15", "2024-03-20"]
        assert detect_column_type(values) == "date"

    def test_boolean_column(self):
        values = ["true", "false", "true", "false"]
        assert detect_column_type(values) == "boolean"

    def test_text_column(self):
        values = ["hello", "world", "foo bar"]
        assert detect_column_type(values) == "text"

    def test_empty_values_return_text(self):
        values = ["", "", None]
        assert detect_column_type(values) == "text"


class TestDetectDateFormat:
    def test_iso_format(self):
        values = ["2024-01-01", "2024-02-15"]
        assert detect_date_format(values) == "%Y-%m-%d"

    def test_us_format(self):
        values = ["01/15/2024", "02/20/2024"]
        assert detect_date_format(values) == "%m/%d/%Y"

    def test_no_date_returns_none(self):
        values = ["hello", "world"]
        assert detect_date_format(values) is None
