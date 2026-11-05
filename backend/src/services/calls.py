"""The call log: recording voice agent conversations when they end."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models import Call, CallOutcome
from repositories import call as call_repo
from repositories import reservation as reservation_repo
from schemas.webhooks import PostCallTranscription, TranscriptTurn

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
