import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TransformationLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transformation_log"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE")
    )
    row_index: Mapped[Optional[int]] = mapped_column(Integer)
    column_name: Mapped[str] = mapped_column(String(255))
    original_value: Mapped[Optional[str]] = mapped_column(Text)
    transformed_value: Mapped[Optional[str]] = mapped_column(Text)
    anomaly_type: Mapped[str] = mapped_column(String(100))
    fix_strategy: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[Optional[float]] = mapped_column(Float)


class AnomalyReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "anomaly_reports"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE")
    )
    total_anomalies: Mapped[int] = mapped_column(Integer, default=0)
    auto_fixed: Mapped[int] = mapped_column(Integer, default=0)
    requires_review: Mapped[int] = mapped_column(Integer, default=0)
    report_json: Mapped[Optional[dict]] = mapped_column(JSON)
