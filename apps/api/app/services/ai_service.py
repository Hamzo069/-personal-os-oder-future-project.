"""Natural-language questions over the user's own expenses.

Flow: question -> (AI) QueryPlan -> validation -> ORM query -> deterministic
answer text. The model never sees the data and never writes SQL; it only
produces a small declarative plan that is validated against the user's own
categories before execution.
"""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.schemas import QueryPlan
from app.models import AICall, Category, Transaction
from app.schemas.insights import AIUsageResponse
from app.services.insights_service import month_key


def _fmt_money(value: Decimal | float | None, currency: str) -> str:
    return f"{Decimal(str(value or 0)):,.2f} {currency}"


def _period_text(plan: QueryPlan) -> str:
    if plan.date_from and plan.date_to:
        return f"between {plan.date_from} and {plan.date_to}"
    if plan.date_from:
        return f"since {plan.date_from}"
    if plan.date_to:
        return f"until {plan.date_to}"
    return "overall"


def _validate_plan(plan: QueryPlan, valid_categories: dict[str, str]) -> QueryPlan:
    """Drop anything the model returned that does not belong to this user."""
    data = plan.model_dump()
    for key in ("date_from", "date_to"):
        if data[key]:
            try:
                date.fromisoformat(data[key])
            except ValueError:
                data[key] = None
    if data["date_from"] and data["date_to"] and data["date_from"] > data["date_to"]:
        data["date_from"], data["date_to"] = data["date_to"], data["date_from"]
    data["categories"] = [
        valid_categories[c.lower()] for c in data["categories"] if c.lower() in valid_categories
    ]
    if data["merchant_contains"]:
        data["merchant_contains"] = data["merchant_contains"].strip()[:100] or None
    return QueryPlan.model_validate(data)


def execute_plan(
    db: Session, user_id: str, plan: QueryPlan, currency: str
) -> tuple[str, dict[str, Any]]:
    filters = [Transaction.user_id == user_id]
    if plan.date_from:
        filters.append(Transaction.date >= date.fromisoformat(plan.date_from))
    if plan.date_to:
        filters.append(Transaction.date <= date.fromisoformat(plan.date_to))
    if plan.categories:
        filters.append(Category.name.in_(plan.categories))
    if plan.merchant_contains:
        filters.append(Transaction.merchant.ilike(f"%{plan.merchant_contains}%"))
    if plan.min_amount is not None:
        filters.append(Transaction.amount >= Decimal(str(plan.min_amount)))
    if plan.max_amount is not None:
        filters.append(Transaction.amount <= Decimal(str(plan.max_amount)))

    def base(*columns: Any) -> Select[Any]:
        stmt = select(*columns).select_from(Transaction)
        stmt = stmt.outerjoin(Category, Category.id == Transaction.category_id)
        return stmt.where(*filters)

    scope = _period_text(plan)
    if plan.categories:
        scope += " in " + ", ".join(plan.categories)
    if plan.merchant_contains:
        scope += f" at merchants matching '{plan.merchant_contains}'"

    if plan.intent in ("sum", "count", "average"):
        total, count = db.execute(
            base(func.coalesce(func.sum(Transaction.amount), 0), func.count(Transaction.id))
        ).one()
        total = Decimal(str(total))
        avg = (total / count).quantize(Decimal("0.01")) if count else Decimal("0.00")
        result = {"total": str(total), "count": int(count), "average": str(avg)}
        if plan.intent == "sum":
            answer = f"You spent {_fmt_money(total, currency)} {scope} across {count} expense(s)."
        elif plan.intent == "count":
            answer = f"You recorded {count} expense(s) {scope}."
        else:
            answer = (
                f"Your average expense {scope} was {_fmt_money(avg, currency)} "
                f"({count} expense(s))."
            )
        return answer, result

    if plan.intent == "by_category":
        rows = db.execute(
            base(Category.name, func.sum(Transaction.amount), func.count(Transaction.id))
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        ).all()
        items = [
            {"label": n or "Uncategorised", "total": str(Decimal(str(t))), "count": int(c)}
            for n, t, c in rows
        ]
        answer = _bullet_answer(f"Spending by category {scope}:", items, currency)
        return answer, {"groups": items}

    if plan.intent == "by_month":
        rows = db.execute(base(Transaction.date, Transaction.amount)).all()
        months: dict[str, tuple[Decimal, int]] = {}
        for d, amount in rows:
            key = month_key(d)
            t, c = months.get(key, (Decimal("0"), 0))
            months[key] = (t + Decimal(str(amount)), c + 1)
        items = [{"label": m, "total": str(t), "count": c} for m, (t, c) in sorted(months.items())]
        answer = _bullet_answer(f"Spending per month {scope}:", items, currency)
        return answer, {"groups": items}

    if plan.intent == "top_merchants":
        rows = db.execute(
            base(Transaction.merchant, func.sum(Transaction.amount), func.count(Transaction.id))
            .group_by(Transaction.merchant)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(plan.limit)
        ).all()
        items = [{"label": m, "total": str(Decimal(str(t))), "count": int(c)} for m, t, c in rows]
        answer = _bullet_answer(f"Top merchants {scope}:", items, currency)
        return answer, {"groups": items}

    # list
    rows = (
        db.scalars(
            base(Transaction)
            .order_by(Transaction.date.desc(), Transaction.amount.desc())
            .limit(plan.limit)
        )
        .unique()
        .all()
    )
    items = [
        {
            "id": tx.id,
            "date": tx.date.isoformat(),
            "merchant": tx.merchant,
            "amount": str(tx.amount),
            "currency": tx.currency,
            "category": tx.category.name if tx.category else None,
        }
        for tx in rows
    ]
    if not items:
        return f"No expenses found {scope}.", {"items": []}
    lines = [f"{len(items)} most recent expense(s) {scope}:"]
    lines += [
        f"- {i['date']} {i['merchant']}: {_fmt_money(Decimal(i['amount']), str(i['currency']))}"
        for i in items
    ]
    return "\n".join(lines), {"items": items}


def _bullet_answer(headline: str, items: list[dict[str, Any]], currency: str) -> str:
    if not items:
        return headline.replace(":", "") + " - nothing found."
    lines = [headline]
    lines += [
        f"- {i['label']}: {_fmt_money(Decimal(i['total']), currency)} ({i['count']})" for i in items
    ]
    return "\n".join(lines)


def answer_question(
    db: Session, provider: AIProvider, user_id: str, question: str, currency: str, today: date
) -> tuple[str, QueryPlan, dict[str, Any]]:
    categories = {
        c.name.lower(): c.name
        for c in db.scalars(select(Category).where(Category.user_id == user_id))
    }
    started = time.perf_counter()
    try:
        planned = provider.plan_query(question, list(categories.values()), today)
    except Exception:
        db.add(
            AICall(
                user_id=user_id,
                kind="query_plan",
                provider=provider.name,
                model="-",
                duration_ms=int((time.perf_counter() - started) * 1000),
                success=False,
            )
        )
        db.commit()
        raise
    db.add(
        AICall(
            user_id=user_id,
            kind="query_plan",
            provider=planned.usage.provider,
            model=planned.usage.model,
            input_tokens=planned.usage.input_tokens,
            output_tokens=planned.usage.output_tokens,
            duration_ms=int((time.perf_counter() - started) * 1000),
            success=True,
        )
    )
    db.commit()
    plan = _validate_plan(planned.plan, categories)
    answer, result = execute_plan(db, user_id, plan, currency)
    return answer, plan, result


def usage_summary(db: Session, user_id: str) -> AIUsageResponse:
    rows = db.execute(
        select(
            AICall.kind,
            func.count(AICall.id),
            func.sum(AICall.input_tokens),
            func.sum(AICall.output_tokens),
        )
        .where(AICall.user_id == user_id)
        .group_by(AICall.kind)
    ).all()
    return AIUsageResponse(
        calls=sum(int(c) for _, c, _, _ in rows),
        input_tokens=sum(int(i or 0) for _, _, i, _ in rows),
        output_tokens=sum(int(o or 0) for _, _, _, o in rows),
        by_kind={k: int(c) for k, c, _, _ in rows},
    )
