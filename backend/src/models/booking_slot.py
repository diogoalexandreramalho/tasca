import enum
from datetime import time

from sqlalchemy import CheckConstraint, Enum, Time
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


class Service(enum.StrEnum):
    LUNCH = "lunch"
    DINNER = "dinner"


class BookingSlot(Base, TimestampMixin):
    """A fixed sitting (e.g. 19:00-20:30). Times are local to the restaurant (Europe/Lisbon)."""

    __tablename__ = "booking_slots"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="time_order"),
        # Declared explicitly rather than via Enum(create_constraint=True), which
        # Alembic autogenerate renders twice.
        CheckConstraint("service IN ('lunch', 'dinner')", name="service"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    service: Mapped[Service] = mapped_column(
        Enum(
            Service,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
            length=16,
        ),
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(Time, unique=True, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
