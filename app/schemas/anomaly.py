import uuid
from typing import Optional

from pydantic import BaseModel


class AnomalyItemResponse(BaseModel):
    row_index: int
    column: str
    original_value: Optional[str]
    anomaly_type: str
    severity: str
    suggested_fix: Optional[str]
    new_value: Optional[str]
    confidence: float


class AnomalyReportResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    total_anomalies: int
    auto_fixed: int
    requires_review: int
    anomalies: list[AnomalyItemResponse] = []

    model_config = {"from_attributes": True}


class HealingResultResponse(BaseModel):
    dataset_id: uuid.UUID
    total_healed: int
    skipped: int
    details: list[dict]


class LineageEntry(BaseModel):
    row_index: Optional[int]
    column_name: str
    original_value: Optional[str]
    transformed_value: Optional[str]
    anomaly_type: str
    fix_strategy: str
    confidence: Optional[float]

    model_config = {"from_attributes": True}
