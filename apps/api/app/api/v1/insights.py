from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBDep
from app.core.errors import ValidationError
from app.schemas.insights import SummaryResponse
from app.services import insights_service

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/summary", response_model=SummaryResponse)
def summary(
    user: CurrentUser,
    db: DBDep,
    date_from: Annotated[dt.date | None, Query()] = None,
    date_to: Annotated[dt.date | None, Query()] = None,
) -> SummaryResponse:
    today = dt.date.today()
    default_from, default_to = insights_service.default_period(today)
    start = date_from or default_from
    end = date_to or default_to
    if start > end:
        raise ValidationError("date_from must not be after date_to")
    if (end - start).days > 366 * 3:
        raise ValidationError("Period must not exceed three years")
    return insights_service.summary(
        db, user.id, date_from=start, date_to=end, currency=user.default_currency
    )
