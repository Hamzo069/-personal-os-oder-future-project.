from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.schemas.transaction import TransactionCreate


class ReceiptRead(ORMModel):
    id: str
    original_filename: str
    media_type: str
    size_bytes: int
    status: str
    extracted: dict[str, Any] | None
    confidence: float | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ReceiptConfirm(TransactionCreate):
    """The user-reviewed (and possibly corrected) transaction for a receipt."""


class ReceiptWithTransaction(BaseModel):
    receipt: ReceiptRead
    transaction_id: str
