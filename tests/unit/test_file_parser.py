import pytest
from app.utils.file_parser import parse_csv, parse_json, parse_file, get_sample_rows


class TestParseCSV:
    def test_standard_csv(self):
        content = b"name,age,city\nAlice,30,NYC\nBob,25,LA\n"
        df = parse_csv(content)
        assert len(df) == 2
        assert list(df.columns) == ["name", "age", "city"]

    def test_semicolon_separated(self):
        content = b"name;age;city\nAlice;30;NYC\nBob;25;LA\n"
        df = parse_csv(content)
        assert len(df.columns) == 3

    def test_tab_separated(self):
        content = b"name\tage\tcity\nAlice\t30\tNYC\n"
        df = parse_csv(content)
        assert len(df.columns) == 3


class TestParseJSON:
    def test_array_of_objects(self):
        content = b'[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
        df = parse_json(content)
        assert len(df) == 2
        assert "name" in df.columns

    def test_nested_data_key(self):
        content = b'{"status": "ok", "data": [{"id": 1}, {"id": 2}]}'
        df = parse_json(content)
        assert len(df) == 2
        assert "id" in df.columns


class TestParseFile:
    def test_csv_extension(self):
        content = b"a,b\n1,2\n"
        df = parse_file("test.csv", content)
        assert len(df) == 1

    def test_json_extension(self):
        content = b'[{"x": 1}]'
        df = parse_file("data.json", content)
        assert "x" in df.columns


class TestGetSampleRows:
    def test_returns_limited_rows(self):
        import pandas as pd

        df = pd.DataFrame({"a": range(100), "b": range(100)})
        samples = get_sample_rows(df, n=3)
        assert len(samples) == 3
        assert samples[0]["a"] == 0
