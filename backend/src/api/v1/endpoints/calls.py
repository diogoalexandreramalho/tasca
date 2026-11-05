import datetime as dt
import uuid
from typing import Literal

from fastapi import APIRouter

from api.v1.deps import DbSession
from models import Reservation
from schemas.call import CallBooking, CallDetail, CallRead, TranscriptLine
from services import calls
from services.calls import CallWithBookings

router = APIRouter(prefix="/calls", tags=["calls"])


def _bookings(c: CallWithBookings) -> list[CallBooking]:
    def booking(r: Reservation, action: Literal["created", "cancelled"]) -> CallBooking:
        return CallBooking(
            id=r.id,
            action=action,
            reservation_date=r.reservation_date,
            start_time=r.booking_slot.start_time,
            party_size=r.party_size,
            customer_name=r.customer.name,
            status=r.status,
        )

    return [booking(r, "created") for r in c.created] + [
        booking(r, "cancelled") for r in c.cancelled
    ]


def _read(c: CallWithBookings) -> CallRead:
    return CallRead(
        id=c.call.id,
        conversation_id=c.call.conversation_id,
        started_at=c.call.started_at,
        duration_secs=c.call.duration_secs,
        outcome=c.call.outcome,
        summary=c.call.summary,
        bookings=_bookings(c),
    )


@router.get("", response_model=list[CallRead])
async def list_calls(session: DbSession, date: dt.date | None = None) -> list[CallRead]:
    """Calls that started on `date` (Lisbon), or the 50 most recent; newest first.

    No transcripts here (lighter, and less personal data on screen): open one call.
    """
    return [_read(c) for c in await calls.list_calls(session, day=date)]


@router.get("/{call_id}", response_model=CallDetail)
async def get_call(session: DbSession, call_id: uuid.UUID) -> CallDetail:
    return _detail(await calls.get_call(session, call_id=call_id))


@router.get("/by-conversation/{conversation_id}", response_model=CallDetail)
async def get_call_by_conversation(session: DbSession, conversation_id: str) -> CallDetail:
    """Open a booking's call: bookings store the ElevenLabs conversation id."""
    return _detail(await calls.get_call_by_conversation(session, conversation_id=conversation_id))


def _detail(c: CallWithBookings) -> CallDetail:
    transcript = (
        [TranscriptLine.model_validate(line) for line in c.call.transcript]
        if c.call.transcript is not None
        else None
    )
    return CallDetail(**_read(c).model_dump(), transcript=transcript)
