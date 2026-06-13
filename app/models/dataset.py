import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Dataset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50))
    original_filename: Mapped[Optional[str]] = mapped_column(String(500))
    row_count: Mapped[Optional[int]] = mapped_column(Integer)
    column_count: Mapped[Optional[int]] = mapped_column(Integer)
    target_table_name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="pending")

    column_mappings: Mapped[list["ColumnMapping"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class ColumnMapping(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "column_mappings"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE")
    )
    source_column: Mapped[str] = mapped_column(String(255))
    target_column: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[Optional[str]] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(100))
    transformation: Mapped[Optional[str]] = mapped_column(String(500))
    confidence: Mapped[Optional[float]] = mapped_column(Float)

    dataset: Mapped["Dataset"] = relationship(back_populates="column_mappings")
