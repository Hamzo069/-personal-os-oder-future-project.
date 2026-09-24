from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentUser, DBDep
from app.schemas.common import Page
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilters,
    TransactionRead,
    TransactionUpdate,
)
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])

FiltersDep = Annotated[TransactionFilters, Depends()]


@router.get("", response_model=Page[TransactionRead])
def list_transactions(filters: FiltersDep, user: CurrentUser, db: DBDep) -> Page[TransactionRead]:
    items, total = transaction_service.list_transactions(db, user.id, filters)
    return Page(
        items=[TransactionRead.model_validate(t) for t in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@router.get("/export", response_class=Response)
def export_transactions(filters: FiltersDep, user: CurrentUser, db: DBDep) -> Response:
    csv_text = transaction_service.export_csv(db, user.id, filters)
    return Response(
        content="﻿" + csv_text,  # BOM so Excel opens UTF-8 correctly
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ledgerlens-transactions.csv"'},
    )


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, user: CurrentUser, db: DBDep) -> TransactionRead:
    return TransactionRead.model_validate(
        transaction_service.create_transaction(db, user.id, payload)
    )


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: str, user: CurrentUser, db: DBDep) -> TransactionRead:
    return TransactionRead.model_validate(
        transaction_service.get_transaction(db, user.id, transaction_id)
    )


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: str, payload: TransactionUpdate, user: CurrentUser, db: DBDep
) -> TransactionRead:
    return TransactionRead.model_validate(
        transaction_service.update_transaction(db, user.id, transaction_id, payload)
    )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: str, user: CurrentUser, db: DBDep) -> None:
    transaction_service.delete_transaction(db, user.id, transaction_id)
