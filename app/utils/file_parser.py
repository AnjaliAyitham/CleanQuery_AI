import io
import json
from typing import Any

import pandas as pd


def detect_encoding(content: bytes) -> str:
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            content.decode(encoding)
            return encoding
        except (UnicodeDecodeError, ValueError):
            continue
    return "utf-8"


def parse_csv(content: bytes) -> pd.DataFrame:
    encoding = detect_encoding(content)
    text = content.decode(encoding)
    for sep in [",", ";", "\t", "|"]:
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, nrows=5)
            if len(df.columns) > 1:
                return pd.read_csv(io.StringIO(text), sep=sep)
        except Exception:
            continue
    return pd.read_csv(io.StringIO(text))


def parse_json(content: bytes) -> pd.DataFrame:
    encoding = detect_encoding(content)
    data = json.loads(content.decode(encoding))
    if isinstance(data, list):
        return pd.json_normalize(data)
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                return pd.json_normalize(value)
        return pd.json_normalize([data])
    raise ValueError("Unsupported JSON structure")


def parse_excel(content: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(content), engine="openpyxl")


def parse_pdf(content: bytes) -> pd.DataFrame:
    import fitz  # pymupdf

    doc = fitz.open(stream=content, filetype="pdf")
    tables = []

    for page in doc:
        page_tables = page.find_tables()
        for table in page_tables:
            df = table.to_pandas()
            if len(df.columns) > 1 and len(df) > 0:
                tables.append(df)

    if tables:
        return pd.concat(tables, ignore_index=True)

    # Fallback: extract text lines and try to parse as structured data
    lines = []
    for page in doc:
        text = page.get_text()
        for line in text.strip().split("\n"):
            if line.strip():
                lines.append(line.strip())

    if not lines:
        raise ValueError("No extractable data found in PDF")

    # Try to detect delimiter in text lines
    for sep in ["\t", "|", ",", ";"]:
        parts = [line.split(sep) for line in lines]
        col_counts = [len(p) for p in parts]
        if col_counts and col_counts[0] > 1 and len(set(col_counts[:10])) <= 2:
            headers = parts[0]
            rows = parts[1:]
            return pd.DataFrame(rows, columns=headers)

    return pd.DataFrame({"content": lines})


def parse_file(filename: str, content: bytes) -> pd.DataFrame:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "csv":
        return parse_csv(content)
    elif ext in ("json", "jsonl"):
        return parse_json(content)
    elif ext in ("xlsx", "xls"):
        return parse_excel(content)
    elif ext == "pdf":
        return parse_pdf(content)
    else:
        try:
            return parse_csv(content)
        except Exception:
            return parse_json(content)


def get_sample_rows(df: pd.DataFrame, n: int = 5) -> list[dict[str, Any]]:
    return df.head(n).fillna("NULL").to_dict(orient="records")
