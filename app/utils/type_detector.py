import re
from typing import Literal

DATE_PATTERNS = [
    (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
    (r"\d{2}/\d{2}/\d{4}", "%m/%d/%Y"),
    (r"\d{2}-\d{2}-\d{4}", "%m-%d-%Y"),
    (r"\d{2}\.\d{2}\.\d{4}", "%d.%m.%Y"),
    (r"\d{4}/\d{2}/\d{2}", "%Y/%m/%d"),
]

CURRENCY_PATTERN = re.compile(r"^[\$€£¥₹][\d,]+\.?\d*$|^[\d,]+\.?\d*[\$€£¥₹]$")
NUMERIC_PATTERN = re.compile(r"^-?[\d,]+\.?\d*$")
BOOLEAN_VALUES = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}


def detect_column_type(
    values: list[str],
) -> Literal["date", "timestamp", "integer", "float", "boolean", "text"]:
    non_null = [v for v in values if v and str(v).strip() and str(v).lower() not in ("nan", "null", "none")]
    if not non_null:
        return "text"

    sample = non_null[:50]

    if all(str(v).strip().lower() in BOOLEAN_VALUES for v in sample):
        return "boolean"

    date_matches = 0
    for val in sample:
        for pattern, _ in DATE_PATTERNS:
            if re.match(pattern, str(val).strip()):
                date_matches += 1
                break
    if date_matches / len(sample) > 0.8:
        return "date"

    numeric_count = sum(1 for v in sample if NUMERIC_PATTERN.match(str(v).strip().replace(",", "")))
    if numeric_count / len(sample) > 0.8:
        has_decimal = any("." in str(v) for v in sample)
        return "float" if has_decimal else "integer"

    return "text"


def detect_date_format(values: list[str]) -> str | None:
    for val in values[:20]:
        val_str = str(val).strip()
        for pattern, fmt in DATE_PATTERNS:
            if re.match(pattern, val_str):
                return fmt
    return None
