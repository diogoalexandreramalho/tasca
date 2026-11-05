from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Call, CallOutcome


async def upsert(
    session: AsyncSession,
    *,
    conversation_id: str,
    started_at: datetime,
    duration_secs: int,
    outcome: CallOutcome,
    summary: str | None,
    transcript: list[dict[str, Any]],
) -> Call:
    """Insert the call, or overwrite it if this conversation was already recorded.

    ElevenLabs retries webhooks, so the same conversation can arrive twice; the
    unique conversation_id turns the second delivery into an update.
    """
    values = {
        "started_at": started_at,
        "duration_secs": duration_secs,
        "outcome": outcome,
        "summary": summary,
        "transcript": transcript,
    }
    upsert_stmt = (
        insert(Call)
        .values(conversation_id=conversation_id, **values)
        .on_conflict_do_update(
            index_elements=[Call.conversation_id],
            set_={**values, "updated_at": func.now()},
        )
        .returning(Call)
    )
    result = await session.execute(upsert_stmt, execution_options={"populate_existing": True})
    call: Call = result.scalar_one()
    return call


async def clear_personal_data_before(session: AsyncSession, cutoff: datetime) -> int:
    """Drop summaries and transcripts of calls that started before `cutoff`.

    Time, duration and outcome stay for statistics. Returns how many calls changed.
    """
    result = await session.execute(
        update(Call)
        .where(
            Call.started_at < cutoff,
            or_(Call.summary.is_not(None), Call.transcript.is_not(None)),
        )
        .values(summary=None, transcript=None, updated_at=func.now())
    )
    return result.rowcount  # type: ignore[attr-defined, no-any-return]
