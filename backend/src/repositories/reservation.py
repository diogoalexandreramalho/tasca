import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from models import BookingSlot, Customer, Reservation, ReservationStatus


def _with_details() -> Select[Reservation]:
    return select(Reservation).options(
        joinedload(Reservation.customer),
        joinedload(Reservation.table),
        joinedload(Reservation.booking_slot),
    )


async def get_by_id(session: AsyncSession, reservation_id: uuid.UUID) -> Reservation | None:
    result = await session.execute(_with_details().where(Reservation.id == reservation_id))
    return result.scalar_one_or_none()


async def taken_table_ids(
    session: AsyncSession, *, reservation_date: date, booking_slot_id: int
) -> set[int]:
    result = await session.execute(
        select(Reservation.table_id).where(
            Reservation.reservation_date == reservation_date,
            Reservation.booking_slot_id == booking_slot_id,
            Reservation.status == ReservationStatus.CONFIRMED,
        )
    )
    return set(result.scalars().all())


async def list_confirmed_by_phone(
    session: AsyncSession, *, phone: str, from_date: date
) -> Sequence[Reservation]:
    result = await session.execute(
        _with_details()
        .join(Reservation.customer)
        .join(Reservation.booking_slot)
        .where(
            Customer.phone == phone,
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.reservation_date >= from_date,
        )
        .order_by(Reservation.reservation_date, BookingSlot.start_time)
    )
    return result.scalars().all()


async def list_confirmed_by_name_and_date(
    session: AsyncSession, *, name: str, reservation_date: date
) -> Sequence[Reservation]:
    """Case-insensitive partial match, so "ana" finds "Ana Silva"."""
    result = await session.execute(
        _with_details()
        .join(Reservation.customer)
        .join(Reservation.booking_slot)
        .where(
            Customer.name.icontains(name.strip(), autoescape=True),
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.reservation_date == reservation_date,
        )
        .order_by(BookingSlot.start_time)
    )
    return result.scalars().all()
