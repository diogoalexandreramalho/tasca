"""The call log: recording voice agent conversations when they end."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import NotFoundError
from models import Call, CallOutcome, Reservation
from repositories import call as call_repo
from repositories import reservation as reservation_repo
from schemas.webhooks import PostCallTranscription, TranscriptTurn
from services.booking_rules import RESTAURANT_TZ

# Our webhook tools. System tools (end_call, language detection) don't make a
# call an "enquiry".
BOOKING_TOOLS = frozenset(
    {"check_availability", "create_reservation", "find_reservations", "cancel_reservation"}
)


def used_booking_tools(transcript: list[TranscriptTurn]) -> bool:
    return any(
        call.tool_name in BOOKING_TOOLS for turn in transcript for call in turn.tool_calls or []
    )


def outcome_of(*, created: bool, cancelled: bool, used_tools: bool) -> CallOutcome:
    """What the call achieved, from facts rather than an AI's opinion.

    A call that both cancels and books (i.e. a change) counts as booked.
    """
    if created:
        return CallOutcome.BOOKED
    if cancelled:
        return CallOutcome.CANCELLED
    if used_tools:
        return CallOutcome.ENQUIRY
    return CallOutcome.NO_ACTION


def minimal_transcript(transcript: list[TranscriptTurn]) -> list[dict[str, str | int]]:
    """Who said what, and when. Tool payloads, timings and metrics are dropped."""
    return [
        {"role": t.role, "message": t.message, "time_in_call_secs": round(t.time_in_call_secs)}
        for t in transcript
        if t.message and t.message.strip()
    ]


async def record_call(session: AsyncSession, data: PostCallTranscription, *, now: datetime) -> Call:
    created, cancelled = await reservation_repo.conversation_activity(session, data.conversation_id)
    call = await call_repo.upsert(
        session,
        conversation_id=data.conversation_id,
        started_at=datetime.fromtimestamp(data.metadata.start_time_unix_secs, tz=UTC),
        duration_secs=data.metadata.call_duration_secs,
        outcome=outcome_of(
            created=created, cancelled=cancelled, used_tools=used_booking_tools(data.transcript)
        ),
        summary=data.analysis.transcript_summary if data.analysis else None,
        transcript=minimal_transcript(data.transcript),
    )

    # Retention, done here so it needs no scheduled job (Render's free plan has none).
    retention = timedelta(days=get_settings().call_transcript_retention_days)
    await call_repo.clear_personal_data_before(session, now - retention)

    await session.commit()
    return call


@dataclass(frozen=True)
class CallWithBookings:
    call: Call
    created: list[Reservation]  # bookings made during the call
    cancelled: list[Reservation]  # bookings cancelled during the call


RECENT_CALLS_LIMIT = 50


async def _with_bookings(session: AsyncSession, calls: Sequence[Call]) -> list[CallWithBookings]:
    reservations = await reservation_repo.list_by_conversations(
        session, [c.conversation_id for c in calls]
    )
    return [
        CallWithBookings(
            call=c,
            created=[r for r in reservations if r.created_in_conversation_id == c.conversation_id],
            cancelled=[
                r for r in reservations if r.cancelled_in_conversation_id == c.conversation_id
            ],
        )
        for c in calls
    ]


async def list_calls(session: AsyncSession, *, day: date | None) -> list[CallWithBookings]:
    """Calls that started on `day` (Lisbon time), or the most recent ones; newest first."""
    if day is None:
        calls = await call_repo.list_recent(session, RECENT_CALLS_LIMIT)
    else:
        start = datetime.combine(day, time.min, tzinfo=RESTAURANT_TZ)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=RESTAURANT_TZ)
        calls = await call_repo.list_started_between(session, start, end)
    return await _with_bookings(session, calls)


async def get_call(session: AsyncSession, *, call_id: uuid.UUID) -> CallWithBookings:
    return await _found(session, await call_repo.get_by_id(session, call_id))


async def get_call_by_conversation(
    session: AsyncSession, *, conversation_id: str
) -> CallWithBookings:
    """The call a booking links to (bookings store the conversation id, not the call's)."""
    return await _found(session, await call_repo.get_by_conversation_id(session, conversation_id))


async def _found(session: AsyncSession, call: Call | None) -> CallWithBookings:
    if call is None:
        raise NotFoundError("Call not found.")
    [result] = await _with_bookings(session, [call])
    return result
