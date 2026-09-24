"""Receipt pipeline: upload -> AI extraction -> user review -> transaction.

Extraction runs as a background task after the upload response is sent, so
the client never waits on the model. The client polls the receipt until its
status is `extracted` (or `failed`) and then shows the review form.
"""

from __future__ import annotations

import logging
import time
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIProvider, CategoryHint, ExtractionContext
from app.ai.schemas import ReceiptExtraction
from app.core.config import Settings
from app.core.db import SessionLocal
from app.core.errors import AppError, ConflictError, NotFoundError, ValidationError
from app.models import AICall, Category, CategoryFeedback, Receipt, ReceiptStatus, Transaction, User
from app.schemas.receipt import ReceiptConfirm
from app.services.category_service import find_category_by_name
from app.services.transaction_service import create_transaction
from app.storage.local import LocalStorage

logger = logging.getLogger(__name__)

# Magic bytes -> media type. We never trust the client's Content-Type header.
_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"%PDF-", "application/pdf"),
]


def sniff_media_type(data: bytes) -> str | None:
    for signature, media_type in _SIGNATURES:
        if data.startswith(signature):
            return media_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def store_upload(
    db: Session,
    storage: LocalStorage,
    settings: Settings,
    user: User,
    *,
    filename: str,
    data: bytes,
) -> Receipt:
    if not data:
        raise ValidationError("Uploaded file is empty")
    if len(data) > settings.max_upload_bytes:
        raise ValidationError(f"File exceeds the {settings.max_upload_mb} MB upload limit")
    media_type = sniff_media_type(data)
    if media_type is None:
        raise ValidationError("Unsupported file type. Upload a JPEG, PNG, WebP or PDF")
    path = storage.save(user.id, media_type, data)
    receipt = Receipt(
        user_id=user.id,
        original_filename=(filename or "receipt")[:255],
        storage_path=path,
        media_type=media_type,
        size_bytes=len(data),
        status=ReceiptStatus.UPLOADED,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


def list_receipts(db: Session, user_id: str, *, status: str | None = None) -> list[Receipt]:
    stmt = select(Receipt).where(Receipt.user_id == user_id)
    if status:
        stmt = stmt.where(Receipt.status == status)
    return list(db.scalars(stmt.order_by(Receipt.created_at.desc())))


def get_receipt(db: Session, user_id: str, receipt_id: str) -> Receipt:
    receipt = db.get(Receipt, receipt_id)
    if receipt is None or receipt.user_id != user_id:
        raise NotFoundError("Receipt not found")
    return receipt


def delete_receipt(db: Session, storage: LocalStorage, user_id: str, receipt_id: str) -> None:
    receipt = get_receipt(db, user_id, receipt_id)
    storage.delete(receipt.storage_path)
    db.delete(receipt)
    db.commit()


def _category_hints(db: Session, user_id: str, limit: int = 30) -> list[CategoryHint]:
    rows = db.execute(
        select(CategoryFeedback.merchant_display, Category.name)
        .join(Category, Category.id == CategoryFeedback.category_id)
        .where(CategoryFeedback.user_id == user_id)
        .order_by(CategoryFeedback.times_confirmed.desc(), CategoryFeedback.updated_at.desc())
        .limit(limit)
    ).all()
    return [CategoryHint(merchant=m, category=c) for m, c in rows]


def run_extraction(receipt_id: str, provider: AIProvider, storage: LocalStorage) -> None:
    """Background task: opens its own session because the request session is closed."""
    db = SessionLocal()
    try:
        receipt = db.get(Receipt, receipt_id)
        if receipt is None:
            return
        user = db.get(User, receipt.user_id)
        if user is None:
            return
        receipt.status = ReceiptStatus.PROCESSING
        receipt.error_message = None
        db.commit()

        categories = [
            c.name for c in db.scalars(select(Category).where(Category.user_id == user.id))
        ]
        context = ExtractionContext(
            categories=categories,
            hints=_category_hints(db, user.id),
            default_currency=user.default_currency,
        )
        started = time.perf_counter()
        try:
            result = provider.extract_receipt(
                storage.read(receipt.storage_path), receipt.media_type, context
            )
        except AppError as exc:
            _record_call(
                db, user.id, "receipt_extraction", provider.name, "-", 0, 0, started, False
            )
            receipt.status = ReceiptStatus.FAILED
            receipt.error_message = exc.message
            db.commit()
            return
        except Exception:
            logger.exception("Receipt extraction crashed for %s", receipt_id)
            _record_call(
                db, user.id, "receipt_extraction", provider.name, "-", 0, 0, started, False
            )
            receipt.status = ReceiptStatus.FAILED
            receipt.error_message = "Unexpected error during extraction"
            db.commit()
            return

        extraction = _normalise(result.extraction, categories, user.default_currency)
        receipt.extracted = extraction.model_dump()
        receipt.confidence = extraction.confidence
        receipt.status = ReceiptStatus.EXTRACTED
        _record_call(
            db, user.id, "receipt_extraction", result.usage.provider, result.usage.model,
            result.usage.input_tokens, result.usage.output_tokens, started, True,
        )  # fmt: skip
        db.commit()
    finally:
        db.close()


def _normalise(
    extraction: ReceiptExtraction, categories: list[str], currency: str
) -> ReceiptExtraction:
    """Defensive clean-up of model output before it is shown to the user."""
    data = extraction.model_dump()
    if data.get("category") and data["category"] not in categories:
        lowered = {c.lower(): c for c in categories}
        data["category"] = lowered.get(str(data["category"]).lower())
    if data.get("date"):
        try:
            date.fromisoformat(str(data["date"])[:10])
            data["date"] = str(data["date"])[:10]
        except ValueError:
            data["date"] = None
    cur = (data.get("currency") or currency).strip().upper()
    data["currency"] = cur if len(cur) == 3 and cur.isalpha() else currency
    if data.get("total_amount") is not None:
        data["total_amount"] = round(abs(float(data["total_amount"])), 2)
    if data.get("vat_amount") is not None:
        data["vat_amount"] = round(abs(float(data["vat_amount"])), 2)
    return ReceiptExtraction.model_validate(data)


def _record_call(
    db: Session, user_id: str, kind: str, provider: str, model: str,
    input_tokens: int, output_tokens: int, started: float, success: bool,
) -> None:  # fmt: skip
    db.add(
        AICall(
            user_id=user_id, kind=kind, provider=provider, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            duration_ms=int((time.perf_counter() - started) * 1000), success=success,
        )
    )  # fmt: skip


def confirm_receipt(
    db: Session, user_id: str, receipt_id: str, data: ReceiptConfirm
) -> Transaction:
    """Create the transaction from the reviewed draft and remember the category choice."""
    receipt = get_receipt(db, user_id, receipt_id)
    if receipt.status == ReceiptStatus.CONFIRMED:
        raise ConflictError("Receipt was already confirmed")
    if receipt.status in (ReceiptStatus.UPLOADED, ReceiptStatus.PROCESSING):
        raise ConflictError("Receipt extraction is still running")
    tx = create_transaction(db, user_id, data, source="receipt", receipt_id=receipt.id)
    if data.category_id:
        remember_category(db, user_id, merchant=data.merchant, category_id=data.category_id)
    receipt.status = ReceiptStatus.CONFIRMED
    db.commit()
    db.refresh(tx)
    return tx


def remember_category(db: Session, user_id: str, *, merchant: str, category_id: str) -> None:
    key = " ".join(merchant.lower().split())[:200]
    if not key:
        return
    feedback = db.scalar(
        select(CategoryFeedback).where(
            CategoryFeedback.user_id == user_id, CategoryFeedback.merchant_key == key
        )
    )
    if feedback is None:
        db.add(
            CategoryFeedback(
                user_id=user_id, merchant_key=key, merchant_display=merchant.strip()[:200],
                category_id=category_id, times_confirmed=1,
            )
        )  # fmt: skip
    elif feedback.category_id == category_id:
        feedback.times_confirmed += 1
    else:
        feedback.category_id = category_id
        feedback.times_confirmed = 1
    db.commit()


def suggested_category_id(db: Session, user_id: str, extracted: dict | None) -> str | None:
    if not extracted:
        return None
    category = find_category_by_name(db, user_id, extracted.get("category"))
    return category.id if category else None
