"""Reservation use cases: availability, create, find, cancel.

Every function takes `now` instead of reading the clock, so behaviour is
deterministic in tests. Services commit; repositories don't.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    BookingRejectedError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from core.phone import normalize_phone
from models import Reservation, ReservationStatus, Service
from repositories import booking_slot as slot_repo
from repositories import customer as customer_repo
from repositories import dining_table as table_repo
from repositories import reservation as reservation_repo
from services.booking_rules import RESTAURANT_TZ, Rejection, check_booking, pick_table, slot_start

# Partial unique index on (table, date, slot) for confirmed rows; see models/reservation.py.
_ONE_CONFIRMED_PER_TABLE = "uq_reservations_table_date_slot_confirmed"


@dataclass(frozen=True)
class SlotAvailability:
    service: Service
    start_time: time
    end_time: time
    available: bool
    reason: Rejection | None  # why it's unavailable


async def get_availability(
    session: AsyncSession, *, reservation_date: date, party_size: int, now: datetime
) -> list[SlotAvailability]:
    slots = await slot_repo.list_all(session)
    tables = await table_repo.list_active(session)

    availability = []
    for slot in slots:
        reason = check_booking(
            reservation_date=reservation_date,
            start_time=slot.start_time,
            party_size=party_size,
            now=now,
        )
        if reason is None:
            taken = await reservation_repo.taken_table_ids(
                session, reservation_date=reservation_date, booking_slot_id=slot.id
            )
            if pick_table(tables, party_size, taken) is None:
                reason = Rejection.FULLY_BOOKED
        availability.append(
            SlotAvailability(
                service=slot.service,
                start_time=slot.start_time,
                end_time=slot.end_time,
                available=reason is None,
                reason=reason,
            )
        )
    return availability


async def create_reservation(
    session: AsyncSession,
    *,
    reservation_date: date,
    start_time: time,
    party_size: int,
    customer_name: str,
    phone: str,
    notes: str | None = None,
    now: datetime,
) -> Reservation:
    name = customer_name.strip()
    if not name:
        raise ValidationAppError("Customer name is required.")
    phone = normalize_phone(phone)

    slot = await slot_repo.get_by_start_time(session, start_time)
    if slot is None:
        raise ValidationAppError(
            f"No sitting starts at {start_time:%H:%M}.", details={"start_time": str(start_time)}
        )

    rejection = check_booking(
        reservation_date=reservation_date, start_time=start_time, party_size=party_size, now=now
    )
    if rejection is not None:
        raise BookingRejectedError(rejection)

    tables = await table_repo.list_active(session)
    customer = await customer_repo.upsert(session, name=name, phone=phone)
    taken = await reservation_repo.taken_table_ids(
        session, reservation_date=reservation_date, booking_slot_id=slot.id
    )

    # Another call can grab the same table between our read and our insert. The
    # unique index rejects the second insert; we mark that table taken and retry.
    while (table := pick_table(tables, party_size, taken)) is not None:
        reservation = Reservation(
            customer_id=customer.id,
            table_id=table.id,
            booking_slot_id=slot.id,
            reservation_date=reservation_date,
            party_size=party_size,
            status=ReservationStatus.CONFIRMED,
            notes=notes.strip() if notes and notes.strip() else None,
        )
        try:
            async with session.begin_nested():
                session.add(reservation)
        except IntegrityError as exc:
            if _ONE_CONFIRMED_PER_TABLE not in str(exc.orig):
                raise
            taken.add(table.id)
            continue

        await session.commit()
        created = await reservation_repo.get_by_id(session, reservation.id)
        assert created is not None
        return created

    await session.rollback()
    raise BookingRejectedError(Rejection.FULLY_BOOKED)


def _upcoming(reservations: Sequence[Reservation], now: datetime) -> list[Reservation]:
    return [
        r for r in reservations if slot_start(r.reservation_date, r.booking_slot.start_time) > now
    ]


async def find_upcoming_by_phone(
    session: AsyncSession, *, phone: str, now: datetime
) -> list[Reservation]:
    today = now.astimezone(RESTAURANT_TZ).date()
    reservations = await reservation_repo.list_confirmed_by_phone(
        session, phone=normalize_phone(phone), from_date=today
    )
    return _upcoming(reservations, now)


async def find_upcoming_by_name_and_date(
    session: AsyncSession, *, name: str, reservation_date: date, now: datetime
) -> list[Reservation]:
    if not name.strip():
        raise ValidationAppError("Name is required.")
    reservations = await reservation_repo.list_confirmed_by_name_and_date(
        session, name=name, reservation_date=reservation_date
    )
    return _upcoming(reservations, now)


async def cancel_reservation(
    session: AsyncSession, *, reservation_id: uuid.UUID, now: datetime
) -> Reservation:
    reservation = await reservation_repo.get_by_id(session, reservation_id)
    if reservation is None:
        raise NotFoundError("Reservation not found.")
    if reservation.status is ReservationStatus.CANCELLED:
        raise ConflictError("Reservation is already cancelled.")
    if slot_start(reservation.reservation_date, reservation.booking_slot.start_time) <= now:
        raise ConflictError("Reservation has already started.")

    reservation.status = ReservationStatus.CANCELLED
    await session.commit()
    return reservation
