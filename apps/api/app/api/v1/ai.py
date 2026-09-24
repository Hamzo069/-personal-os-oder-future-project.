from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends

from app.api.deps import AIDep, CurrentUser, DBDep, limit_ai
from app.schemas.insights import AIQueryRequest, AIQueryResponse, AIUsageResponse
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/query", response_model=AIQueryResponse, dependencies=[Depends(limit_ai)])
def query(
    payload: AIQueryRequest, user: CurrentUser, db: DBDep, provider: AIDep
) -> AIQueryResponse:
    answer, plan, result = ai_service.answer_question(
        db, provider, user.id, payload.question, user.default_currency, dt.date.today()
    )
    return AIQueryResponse(
        question=payload.question, answer=answer, plan=plan.model_dump(), result=result
    )


@router.get("/usage", response_model=AIUsageResponse)
def usage(user: CurrentUser, db: DBDep) -> AIUsageResponse:
    return ai_service.usage_summary(db, user.id)
