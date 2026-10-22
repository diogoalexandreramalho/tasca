"""Tools the voice agent calls (ElevenLabs "server tools" / webhooks).

Each tool is a thin translation layer:
  1. ElevenLabs POSTs the parameters the model filled in (validated by the
     request schema).
  2. We call the same service the dashboard uses, so the booking rules live in
     one place.
  3. We reply with only the facts the model needs next (see schemas/agent.py).

All routes require the X-Agent-Secret header (see `require_agent` in router.py).
"""

import uuid
from collections.abc import Sequence
from datetime import date, datetime, time

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.deps import DbSession, Now
from core.exceptions import BookingRejectedError, NotFoundError, ValidationAppError
from core.phone import normalize_phone
from models import ReservationStatus
from schemas.agent import (
    AgentReservation,
    CancelReservationReply,
    CancelReservationRequest,
    CheckAvailabilityReply,
    CheckAvailabilityRequest,
    CreateReservationReply,
    CreateReservationRequest,
    FindReservationsReply,
    FindReservationsRequest,
)
from services import reservations, restaurant
from services.booking_rules import Rejection, slot_start

router = APIRouter(prefix="/agent", tags=["agent"])


def day_reason(reasons: Sequence[Rejection]) -> Rejection:
    """One reason for a whole day, from the reason each sitting can't be booked.

    Prefers what the caller can act on: a wrong party size or a closed day beats
    "fully booked". A mix of full, already-started and less-than-an-hour-away
    sittings is just "fully booked" from the caller's point of view.
    """
    for reason in (
        Rejection.PARTY_SIZE_OUT_OF_RANGE,
        Rejection.CLOSED_DAY,
        Rejection.TOO_FAR_AHEAD,
    ):
        if reason in reasons:
            return reason
    if set(reasons) == {Rejection.IN_THE_PAST}:
        return Rejection.IN_THE_PAST
    return Rejection.FULLY_BOOKED


async def free_times(
    session: AsyncSession, *, day: date, party_size: int, now: datetime
) -> tuple[list[str], list[Rejection]]:
    """Free start times ("HH:MM") for the party, and why the other sittings aren't."""
    slots = await reservations.get_availability(
        session, reservation_date=day, party_size=party_size, now=now
    )
    # "HH:MM", exactly what create_reservation accepts, so the model passes it
    # straight through instead of reformatting a spoken time.
    times = [s.start_time.strftime("%H:%M") for s in slots if s.available]
    reasons = [s.reason for s in slots if s.reason is not None]
    return times, reasons


# response_model_exclude_none: leave unused fields out entirely, so the model
# only ever sees fields that mean something.
@router.post(
    "/check-availability",
    response_model=CheckAvailabilityReply,
    response_model_exclude_none=True,
)
async def check_availability(
    session: DbSession, now: Now, body: CheckAvailabilityRequest
) -> CheckAvailabilityReply:
    """Which sittings on a date still have a table for the party."""
    times, reasons = await free_times(session, day=body.date, party_size=body.party_size, now=now)
    if times:
        return CheckAvailabilityReply(available_times=times)
    return CheckAvailabilityReply(available_times=[], reason=day_reason(reasons))


@router.post(
    "/create-reservation",
    response_model=CreateReservationReply,
    response_model_exclude_none=True,
)
async def create_reservation(
    session: DbSession, now: Now, body: CreateReservationRequest
) -> CreateReservationReply:
    """Book a table. Safe to call twice: a repeat returns `already_booked`."""
    # 1. Check the inputs the model collected, so a bad one comes back as
    #    "ask again for X" rather than an error.
    name = body.name.strip()
    if not name:
        return CreateReservationReply(status="invalid", field="name")
    try:
        phone = normalize_phone(body.phone)
    except ValidationAppError:
        return CreateReservationReply(status="invalid", field="phone")
    try:
        start = time.fromisoformat(body.time)
    except ValueError:
        return CreateReservationReply(status="invalid", field="time")
    sittings = {s.start_time for s in await restaurant.list_slots(session)}
    if start not in sittings:
        return CreateReservationReply(status="invalid", field="time")

    # 2. Retries: the model or the network may send the same booking twice.
    #    Check *before* creating; afterwards a second table would already be taken.
    existing = await reservations.find_upcoming_by_phone(session, phone=phone, now=now)
    if any(
        r.reservation_date == body.date and r.booking_slot.start_time == start for r in existing
    ):
        return CreateReservationReply(status="already_booked")

    # 3. Book through the same service as the dashboard (rules, table choice,
    #    double-booking protection all live there).
    try:
        await reservations.create_reservation(
            session,
            reservation_date=body.date,
            start_time=start,
            party_size=body.party_size,
            customer_name=name,
            phone=phone,
            notes=body.notes,
            now=now,
        )
    except BookingRejectedError as exc:
        reason = Rejection(exc.reason)
        if reason is not Rejection.FULLY_BOOKED:
            return CreateReservationReply(status="rejected", reason=reason)
        # Someone may have taken the table since check_availability: offer what's left.
        times, _ = await free_times(session, day=body.date, party_size=body.party_size, now=now)
        return CreateReservationReply(status="rejected", reason=reason, available_times=times)

    return CreateReservationReply(status="booked")


@router.post(
    "/find-reservations",
    response_model=FindReservationsReply,
    response_model_exclude_none=True,
)
async def find_reservations(
    session: DbSession, now: Now, body: FindReservationsRequest
) -> FindReservationsReply:
    """The caller's upcoming bookings. Phone is required on purpose: knowing the
    number a booking was made with is what proves it's theirs, so nobody can ask
    "is there a booking for João?" and learn about other people's plans."""
    try:
        phone = normalize_phone(body.phone)
    except ValidationAppError:
        return FindReservationsReply(reservations=[], field="phone")

    found = await reservations.find_upcoming_by_phone(session, phone=phone, now=now)
    if body.date is not None:
        found = [r for r in found if r.reservation_date == body.date]
    return FindReservationsReply(
        reservations=[
            AgentReservation(
                id=str(r.id),
                date=r.reservation_date,
                time=r.booking_slot.start_time.strftime("%H:%M"),
                party_size=r.party_size,
                name=r.customer.name,
            )
            for r in found
        ]
    )


@router.post("/cancel-reservation", response_model=CancelReservationReply)
async def cancel_reservation(
    session: DbSession, now: Now, body: CancelReservationRequest
) -> CancelReservationReply:
    """Cancel one of the caller's bookings, by the id find_reservations returned.

    The phone must match the booking's, so a confused or manipulated model can't
    cancel a stranger's booking just by holding an id. A wrong id and someone
    else's booking both answer `not_found`, revealing nothing about which.
    """
    try:
        reservation_id = uuid.UUID(body.reservation_id)
        phone = normalize_phone(body.phone)
        reservation = await reservations.get_reservation(session, reservation_id=reservation_id)
    except (ValueError, ValidationAppError, NotFoundError):
        return CancelReservationReply(status="not_found")
    if reservation.customer.phone != phone:
        return CancelReservationReply(status="not_found")

    # Checked here (the service checks again) so each case gets its own status.
    if reservation.status is ReservationStatus.CANCELLED:
        return CancelReservationReply(status="already_cancelled")
    if slot_start(reservation.reservation_date, reservation.booking_slot.start_time) <= now:
        return CancelReservationReply(status="too_late")

    await reservations.cancel_reservation(session, reservation_id=reservation_id, now=now)
    return CancelReservationReply(status="cancelled")
