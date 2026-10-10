import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.booking_slot import BookingSlot
    from models.customer import Customer
    from models.dining_table import DiningTable


class ReservationStatus(enum.StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("party_size BETWEEN 1 AND 8", name="party_size"),
        # Declared explicitly rather than via Enum(create_constraint=True), which
        # Alembic autogenerate renders twice.
        CheckConstraint("status IN ('confirmed', 'cancelled')", name="status"),
        # One confirmed booking per table per sitting. Cancelled rows are kept for
        # history and don't block the table. This is what makes double-booking
        # impossible even when two calls race for the last table.
        Index(
            "uq_reservations_table_date_slot_confirmed",
            "table_id",
            "reservation_date",
            "booking_slot_id",
            unique=True,
            postgresql_where=text("status = 'confirmed'"),
        ),
        Index("ix_reservations_date_slot", "reservation_date", "booking_slot_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True
    )
    table_id: Mapped[int] = mapped_column(ForeignKey("dining_tables.id"), nullable=False)
    booking_slot_id: Mapped[int] = mapped_column(ForeignKey("booking_slots.id"), nullable=False)
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False)
    party_size: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(
            ReservationStatus,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
            length=16,
        ),
        nullable=False,
        default=ReservationStatus.CONFIRMED,
    )
    # Free text. Allergies start with "Alergia:" so the dashboard can highlight them.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # lazy="raise": async sessions can't lazy-load, so load these explicitly
    # (see repositories/reservation.py) and fail loudly if we forget.
    customer: Mapped["Customer"] = relationship(lazy="raise")
    table: Mapped["DiningTable"] = relationship(lazy="raise")
    booking_slot: Mapped["BookingSlot"] = relationship(lazy="raise")
