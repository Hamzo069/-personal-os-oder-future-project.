from __future__ import annotations

import csv
import io
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Transaction
from app.schemas.transaction import TransactionCreate, TransactionFilters, TransactionUpdate
from app.services.category_service import get_category


def _apply_filters(stmt: Select, user_id: str, f: TransactionFilters) -> Select:
    stmt = stmt.where(Transaction.user_id == user_id)
    if f.date_from:
        stmt = stmt.where(Transaction.date >= f.date_from)
    if f.date_to:
        stmt = stmt.where(Transaction.date <= f.date_to)
    if f.category_id:
        stmt = stmt.where(Transaction.category_id == f.category_id)
    if f.min_amount is not None:
        stmt = stmt.where(Transaction.amount >= f.min_amount)
    if f.max_amount is not None:
        stmt = stmt.where(Transaction.amount <= f.max_amount)
    if f.source:
        stmt = stmt.where(Transaction.source == f.source)
    if f.q:
        pattern = f"%{f.q.strip()}%"
        stmt = stmt.where(
            or_(
                Transaction.merchant.ilike(pattern),
                Transaction.description.ilike(pattern),
                Transaction.notes.ilike(pattern),
            )
        )
    return stmt


_SORTS: dict[str, tuple[Any, ...]] = {
    "date_desc": (Transaction.date.desc(), Transaction.created_at.desc()),
    "date_asc": (Transaction.date.asc(), Transaction.created_at.asc()),
    "amount_desc": (Transaction.amount.desc(), Transaction.date.desc()),
    "amount_asc": (Transaction.amount.asc(), Transaction.date.desc()),
}


def list_transactions(
    db: Session, user_id: str, f: TransactionFilters
) -> tuple[list[Transaction], int]:
    base = _apply_filters(select(Transaction), user_id, f)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(*_SORTS[f.sort]).offset((f.page - 1) * f.page_size).limit(f.page_size)
    return list(db.scalars(stmt).unique()), int(total)


def get_transaction(db: Session, user_id: str, transaction_id: str) -> Transaction:
    tx = db.get(Transaction, transaction_id)
    if tx is None or tx.user_id != user_id:
        raise NotFoundError("Transaction not found")
    return tx


def _validate_category(db: Session, user_id: str, category_id: str | None) -> None:
    if category_id is not None:
        get_category(db, user_id, category_id)  # raises NotFoundError for foreign/invalid ids


def create_transaction(
    db: Session,
    user_id: str,
    data: TransactionCreate,
    *,
    source: str = "manual",
    receipt_id: str | None = None,
) -> Transaction:
    _validate_category(db, user_id, data.category_id)
    tx = Transaction(user_id=user_id, source=source, receipt_id=receipt_id, **data.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def update_transaction(
    db: Session, user_id: str, transaction_id: str, data: TransactionUpdate
) -> Transaction:
    tx = get_transaction(db, user_id, transaction_id)
    changes = data.model_dump(exclude_unset=True)
    if "category_id" in changes:
        _validate_category(db, user_id, changes["category_id"])
    if changes.get("currency"):
        changes["currency"] = changes["currency"].upper()
    for key, value in changes.items():
        setattr(tx, key, value)
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, user_id: str, transaction_id: str) -> None:
    tx = get_transaction(db, user_id, transaction_id)
    db.delete(tx)
    db.commit()


def export_csv(db: Session, user_id: str, f: TransactionFilters) -> str:
    stmt = _apply_filters(select(Transaction), user_id, f).order_by(Transaction.date.asc())
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(
        ["date", "merchant", "description", "amount", "currency", "vat_rate", "vat_amount",
         "category", "source", "notes"]
    )  # fmt: skip
    for tx in db.scalars(stmt).unique():
        writer.writerow(
            [
                tx.date.isoformat(),
                tx.merchant,
                tx.description or "",
                _fmt(tx.amount),
                tx.currency,
                _fmt(tx.vat_rate),
                _fmt(tx.vat_amount),
                tx.category.name if tx.category else "",
                tx.source,
                tx.notes or "",
            ]
        )
    return buffer.getvalue()


def _fmt(value: Decimal | None) -> str:
    return "" if value is None else f"{value:.2f}"
