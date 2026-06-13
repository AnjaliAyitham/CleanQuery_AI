import uuid
from typing import Any, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    id: uuid.UUID
    question: str
    generated_sql: str
    explanation: str
    tables_used: list[str]
    assumptions: list[str]
    results: list[dict[str, Any]]
    row_count: int
    execution_time_ms: int


class QueryHistoryItem(BaseModel):
    id: uuid.UUID
    natural_language_query: str
    generated_sql: Optional[str]
    status: str
    row_count: Optional[int]
    execution_time_ms: Optional[int]
    explanation: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class SchemaContextResponse(BaseModel):
    tables: list[dict[str, Any]]
