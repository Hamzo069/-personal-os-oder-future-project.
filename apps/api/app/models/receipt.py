from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ReceiptStatus:
    UPLOADED = "uploaded"  # stored, extraction not started yet
    PROCESSING = "processing"  # extraction running
    EXTRACTED = "extracted"  # AI draft ready for user review
    CONFIRMED = "confirmed"  # user confirmed -> transaction created
    FAILED = "failed"  # extraction failed; user can retry or enter manually

    ALL = (UPLOADED, PROCESSING, EXTRACTED, CONFIRMED, FAILED)


class Receipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An uploaded receipt file plus the AI extraction draft."""

    __tablename__ = "receipts"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ReceiptStatus.UPLOADED, nullable=False)
    extracted: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
