from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import Category, Transaction


def list_categories(db: Session, user_id: str) -> list[Category]:
    return list(
        db.scalars(select(Category).where(Category.user_id == user_id).order_by(Category.name))
    )


def get_category(db: Session, user_id: str, category_id: str) -> Category:
    category = db.get(Category, category_id)
    if category is None or category.user_id != user_id:
        raise NotFoundError("Category not found")
    return category


def create_category(db: Session, user_id: str, *, name: str, color: str) -> Category:
    name = name.strip()
    exists = db.scalar(
        select(Category).where(
            Category.user_id == user_id, func.lower(Category.name) == name.lower()
        )
    )
    if exists:
        raise ConflictError("A category with this name already exists")
    category = Category(user_id=user_id, name=name, color=color)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session, user_id: str, category_id: str, *, name: str | None, color: str | None
) -> Category:
    category = get_category(db, user_id, category_id)
    if name is not None and name.strip().lower() != category.name.lower():
        duplicate = db.scalar(
            select(Category).where(
                Category.user_id == user_id,
                func.lower(Category.name) == name.strip().lower(),
                Category.id != category_id,
            )
        )
        if duplicate:
            raise ConflictError("A category with this name already exists")
    if name is not None:
        category.name = name.strip()
    if color is not None:
        category.color = color
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, user_id: str, category_id: str) -> int:
    """Delete a category. Transactions keep existing and become uncategorised."""
    category = get_category(db, user_id, category_id)
    affected = db.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.category_id == category_id)
    )
    db.delete(category)
    db.commit()
    return int(affected or 0)


def find_category_by_name(db: Session, user_id: str, name: str | None) -> Category | None:
    if not name:
        return None
    return db.scalar(
        select(Category).where(
            Category.user_id == user_id, func.lower(Category.name) == name.strip().lower()
        )
    )
