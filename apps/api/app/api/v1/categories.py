from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBDep
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(user: CurrentUser, db: DBDep) -> list[CategoryRead]:
    return [CategoryRead.model_validate(c) for c in category_service.list_categories(db, user.id)]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, user: CurrentUser, db: DBDep) -> CategoryRead:
    category = category_service.create_category(db, user.id, name=payload.name, color=payload.color)
    return CategoryRead.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: str, payload: CategoryUpdate, user: CurrentUser, db: DBDep
) -> CategoryRead:
    category = category_service.update_category(
        db, user.id, category_id, name=payload.name, color=payload.color
    )
    return CategoryRead.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: str, user: CurrentUser, db: DBDep) -> None:
    category_service.delete_category(db, user.id, category_id)
