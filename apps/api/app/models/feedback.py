from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class CategoryFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Remembers which category a user assigned to a merchant.

    This is the "learning loop": corrections are fed back to the AI as
    few-shot examples so category suggestions get better over time.
    """

    __tablename__ = "category_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "merchant_key", name="uq_feedback_user_merchant"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    merchant_key: Mapped[str] = mapped_column(String(200), nullable=False)
    merchant_display: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    times_confirmed: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
