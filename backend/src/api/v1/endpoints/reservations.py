import datetime as dt
import uuid
from collections.abc import Sequence

from fastapi import APIRouter, Depends, status

from api.v1.deps import CurrentViewer, DbSession, Now, Viewer, require_admin
from core.exceptions import ForbiddenError, ValidationAppError
from core.privacy import mask_phone, mask_phone_numbers
from models import Reservation
from schemas.reservation import ReservationCreate, ReservationRead
from services import reservations

router = APIRouter(prefix="/reservations", tags=["reservations"])


def _for(viewer: Viewer, r: Reservation) -> ReservationRead:
    """The booking as this viewer may see it: guests get phone numbers masked."""
    read = ReservationRead.model_validate(r)
    if viewer.is_guest:
        read.customer.phone = mask_phone(read.customer.phone)
        if read.notes is not None:
            read.notes = mask_phone_numbers(read.notes)
    return read


@router.get("", response_model=list[ReservationRead])
async def list_reservations(
    session: DbSession,
    now: Now,
    viewer: CurrentViewer,
    date: dt.date | None = None,  # `dt.` because the query param is also called `date`
    phone: str | None = None,
    name: str | None = None,
) -> list[ReservationRead]:
    """Confirmed bookings. Use exactly one of:

    - `date`: the day view, every booking that day by sitting then table
    - `phone`: the customer's upcoming bookings
    - `name`: upcoming bookings on any date whose name contains `name` (max 50)
    - `name` + `date`: upcoming bookings on that date whose name contains `name`

    Guests can't search by phone: it would confirm whether a number has bookings.
    """
    found: Sequence[Reservation]
    if phone is not None and date is None and name is None:
        if viewer.is_guest:
            raise ForbiddenError("Searching by phone isn't available in the demo.")
        found = await reservations.find_upcoming_by_phone(session, phone=phone, now=now)
    elif name is not None and phone is None:
        if date is None:
            found = await reservations.find_upcoming_by_name(session, name=name, now=now)
        else:
            found = await reservations.find_upcoming_by_name_and_date(
                session, name=name, reservation_date=date, now=now
            )
    elif date is not None and phone is None and name is None:
        found = await reservations.list_day(session, reservation_date=date)
    else:
        raise ValidationAppError(
            "Filter by `date`, by `phone`, by `name`, or by `name` and `date`."
        )
    return [_for(viewer, r) for r in found]


@router.get("/{reservation_id}", response_model=ReservationRead)
async def get_reservation(
    session: DbSession, viewer: CurrentViewer, reservation_id: uuid.UUID
) -> ReservationRead:
    return _for(viewer, await reservations.get_reservation(session, reservation_id=reservation_id))


@router.post(
    "",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
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


@router.post(
    "/{reservation_id}/cancel",
    response_model=ReservationRead,
    dependencies=[Depends(require_admin)],
)
async def cancel_reservation(
    session: DbSession, now: Now, reservation_id: uuid.UUID
) -> Reservation:
    """Cancel a confirmed booking. The table becomes free; the booking is kept as history."""
    return await reservations.cancel_reservation(session, reservation_id=reservation_id, now=now)
