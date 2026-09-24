"""Aggregations for the dashboard. Pure SQL grouping - no AI involved."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Receipt, ReceiptStatus, Transaction
from app.schemas.insights import (
    CategoryTotal,
    MerchantTotal,
    MonthTotal,
    SummaryResponse,
)

ZERO = Decimal("0.00")


def _dec(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def default_period(today: date) -> tuple[date, date]:
    """Last 6 full months up to today (inclusive)."""
    start = (today.replace(day=1) - timedelta(days=150)).replace(day=1)
    return start, today


def summary(
    db: Session, user_id: str, *, date_from: date, date_to: date, currency: str
) -> SummaryResponse:
    base_where = (
        Transaction.user_id == user_id,
        Transaction.date >= date_from,
        Transaction.date <= date_to,
    )
    total, count, vat_total = db.execute(
        select(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
            func.coalesce(func.sum(Transaction.vat_amount), 0),
        ).where(*base_where)
    ).one()

    period_days = (date_to - date_from).days + 1
    prev_to = date_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=period_days - 1)
    previous_total = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.date >= prev_from,
            Transaction.date <= prev_to,
        )
    )
    change = None
    if previous_total:
        change = round(
            float(
                (Decimal(str(total)) - Decimal(str(previous_total)))
                / Decimal(str(previous_total))
                * 100
            ),
            1,
        )

    by_category_rows = db.execute(
        select(
            Transaction.category_id,
            Category.name,
            Category.color,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(*base_where)
        .group_by(Transaction.category_id, Category.name, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()
    by_category = [
        CategoryTotal(
            category_id=cid,
            category_name=name or "Uncategorised",
            color=color or "#9ca3af",
            total=_dec(amount),
            count=int(cnt),
        )
        for cid, name, color, amount, cnt in by_category_rows
    ]

    # Month grouping in Python keeps this portable across SQLite and PostgreSQL.
    month_totals: dict[str, tuple[Decimal, int]] = {}
    cursor = date_from.replace(day=1)
    while cursor <= date_to:
        month_totals[month_key(cursor)] = (ZERO, 0)
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    for d, amount in db.execute(select(Transaction.date, Transaction.amount).where(*base_where)):
        key = month_key(d)
        prev_total, prev_count = month_totals.get(key, (ZERO, 0))
        month_totals[key] = (prev_total + _dec(amount), prev_count + 1)
    by_month = [MonthTotal(month=m, total=t, count=c) for m, (t, c) in sorted(month_totals.items())]

    merchants = db.execute(
        select(Transaction.merchant, func.sum(Transaction.amount), func.count(Transaction.id))
        .where(*base_where)
        .group_by(Transaction.merchant)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    ).all()
    top_merchants = [
        MerchantTotal(merchant=m, total=_dec(t), count=int(c)) for m, t, c in merchants
    ]

    pending = db.scalar(
        select(func.count(Receipt.id)).where(
            Receipt.user_id == user_id, Receipt.status == ReceiptStatus.EXTRACTED
        )
    )

    total_dec = _dec(total)
    return SummaryResponse(
        date_from=date_from,
        date_to=date_to,
        currency=currency,
        total=total_dec,
        count=int(count),
        vat_total=_dec(vat_total),
        average=(total_dec / count).quantize(Decimal("0.01")) if count else ZERO,
        previous_period_total=_dec(previous_total),
        change_percent=change,
        receipts_pending_review=int(pending or 0),
        by_category=by_category,
        by_month=by_month,
        top_merchants=top_merchants,
    )
