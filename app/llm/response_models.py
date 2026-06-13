from typing import Literal

from pydantic import BaseModel


class ColumnMappingItem(BaseModel):
    source_column: str
    target_column: str
    target_type: Literal["text", "integer", "float", "date", "timestamp", "boolean", "json"]
    transformation: str | None = None
    confidence: float


class SchemaMappingResponse(BaseModel):
    mappings: list[ColumnMappingItem]
    suggested_table_name: str
    notes: list[str]


class AnomalyItem(BaseModel):
    row_index: int
    column: str
    original_value: str | None
    anomaly_type: Literal[
        "mixed_format", "corrupted", "missing", "outlier", "duplicate", "inconsistent"
    ]
    severity: Literal["low", "medium", "high"]
    suggested_fix: str | None
    new_value: str | None
    confidence: float


class AnomalyClassificationResponse(BaseModel):
    anomalies: list[AnomalyItem]
    summary: str


class GeneratedQuery(BaseModel):
    sql: str
    explanation: str
    tables_used: list[str]
    assumptions: list[str]


class QueryExplanation(BaseModel):
    summary: str
    key_findings: list[str]
