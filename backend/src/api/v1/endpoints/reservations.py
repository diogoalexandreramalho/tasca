import datetime as dt
import uuid
from collections.abc import Sequence

from fastapi import APIRouter, status

from api.v1.deps import DbSession, Now
from core.exceptions import ValidationAppError
from models import Reservation
from schemas.reservation import ReservationCreate, ReservationRead
from services import reservations

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("", response_model=list[ReservationRead])
async def list_reservations(
    session: DbSession,
    now: Now,
    date: dt.date | None = None,  # `dt.` because the query param is also called `date`
    phone: str | None = None,
    name: str | None = None,
) -> Sequence[Reservation]:
    """Confirmed bookings. Use exactly one of:

    - `date`: the day view, every booking that day by sitting then table
    - `phone`: the customer's upcoming bookings
    - `name`: upcoming bookings on any date whose name contains `name` (max 50)
    - `name` + `date`: upcoming bookings on that date whose name contains `name`
    """
    if phone is not None and date is None and name is None:
        return await reservations.find_upcoming_by_phone(session, phone=phone, now=now)
    if name is not None and phone is None:
        if date is None:
            return await reservations.find_upcoming_by_name(session, name=name, now=now)
        return await reservations.find_upcoming_by_name_and_date(
            session, name=name, reservation_date=date, now=now
        )
    if date is not None and phone is None and name is None:
        return await reservations.list_day(session, reservation_date=date)
    raise ValidationAppError("Filter by `date`, by `phone`, by `name`, or by `name` and `date`.")


@router.get("/{reservation_id}", response_model=ReservationRead)
async def get_reservation(session: DbSession, reservation_id: uuid.UUID) -> Reservation:
    return await reservations.get_reservation(session, reservation_id=reservation_id)


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    session: DbSession, now: Now, payload: ReservationCreate
) -> Reservation:
    """Book the smallest free table that fits. 409 `booking_rejected` says why if it can't."""
    return await reservations.create_reservation(
        session,
        reservation_date=payload.reservation_date,
        start_time=payload.start_time,
        party_size=payload.party_size,
        customer_name=payload.customer_name,
        phone=payload.phone,
        notes=payload.notes,
        now=now,
    )


@router.post("/{reservation_id}/cancel", response_model=ReservationRead)
async def cancel_reservation(
    session: DbSession, now: Now, reservation_id: uuid.UUID
) -> Reservation:
    """Cancel a confirmed booking. The table becomes free; the booking is kept as history."""
    return await reservations.cancel_reservation(session, reservation_id=reservation_id, now=now)
