from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

# Seeded for every new user. Kept deliberately small - users can add their own.
DEFAULT_CATEGORIES: list[tuple[str, str]] = [
    ("Software & Subscriptions", "#6366f1"),
    ("Office & Equipment", "#0ea5e9"),
    ("Travel & Transport", "#f59e0b"),
    ("Food & Drinks", "#22c55e"),
    ("Education & Books", "#a855f7"),
    ("Marketing", "#ec4899"),
    ("Telecommunication", "#14b8a6"),
    ("Insurance & Fees", "#64748b"),
    ("Rent & Utilities", "#ef4444"),
    ("Other", "#9ca3af"),
]


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_category_user_name"),)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#9ca3af", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
