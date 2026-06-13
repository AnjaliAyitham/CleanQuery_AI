import uuid
from typing import Optional

from pydantic import BaseModel


class DatasetResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    original_filename: Optional[str]
    row_count: Optional[int]
    column_count: Optional[int]
    target_table_name: Optional[str]
    status: str

    model_config = {"from_attributes": True}


class ColumnMappingResponse(BaseModel):
    source_column: str
    target_column: str
    target_type: str
    transformation: Optional[str]
    confidence: Optional[float]

    model_config = {"from_attributes": True}


class DatasetDetailResponse(DatasetResponse):
    column_mappings: list[ColumnMappingResponse] = []


class MappingApproval(BaseModel):
    mappings: list[ColumnMappingResponse]
    table_name: str
