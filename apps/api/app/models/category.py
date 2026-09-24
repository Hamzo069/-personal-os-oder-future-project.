from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

# Seeded for every new user. Kept deliberately small - users can add their own.
DEFAULT_CATEGORIES: list[tuple[str, str]] = [
    # Colors: a CVD-safe categorical palette in fixed order; "Other" is neutral.
    ("Software & Subscriptions", "#2a78d6"),
    ("Office & Equipment", "#eb6834"),
    ("Travel & Transport", "#1baf7a"),
    ("Food & Drinks", "#eda100"),
    ("Education & Books", "#e87ba4"),
    ("Marketing", "#008300"),
    ("Telecommunication", "#4a3aa7"),
    ("Rent & Utilities", "#e34948"),
    ("Insurance & Fees", "#52514e"),
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
