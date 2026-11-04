import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


class CallOutcome(enum.StrEnum):
    """What the call achieved, from what actually happened in our database."""

    BOOKED = "booked"  # a reservation was created during the call
    CANCELLED = "cancelled"  # a reservation was cancelled during the call
    ENQUIRY = "enquiry"  # tools were used (availability, lookup) but nothing changed
    NO_ACTION = "no_action"  # no tools at all (off-topic question, hung up early)


class Call(Base, TimestampMixin):
    """One voice agent conversation, as reported by ElevenLabs when it ends.

    Linked to reservations through `conversation_id` (see Reservation's
    created_in/cancelled_in_conversation_id), not a foreign key: the bookings are
    written during the call, before this row exists.
    """

    __tablename__ = "calls"
    __table_args__ = (
        CheckConstraint("duration_secs >= 0", name="duration_positive"),
        # Declared explicitly rather than via Enum(create_constraint=True), which
        # Alembic autogenerate renders twice.
        CheckConstraint(
            "outcome IN ('booked', 'cancelled', 'enquiry', 'no_action')", name="outcome"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    duration_secs: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[CallOutcome] = mapped_column(
        Enum(
            CallOutcome,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
            length=16,
        ),
        nullable=False,
    )
    # Personal data (names, phone numbers): cleared after a retention period,
    # while time, duration and outcome are kept for statistics.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [{"role": "agent" | "user", "message": str, "time_in_call_secs": int}, ...]
    transcript: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
