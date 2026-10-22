"""Tools the voice agent calls (ElevenLabs "server tools" / webhooks).

Each tool is a thin translation layer:
  1. ElevenLabs POSTs the parameters the model filled in (validated by the
     request schema).
  2. We call the same service the dashboard uses, so the booking rules live in
     one place.
  3. We reply with only the facts the model needs next (see schemas/agent.py).

All routes require the X-Agent-Secret header (see `require_agent` in router.py).
"""

from collections.abc import Sequence

from fastapi import APIRouter

from api.v1.deps import DbSession, Now
from schemas.agent import CheckAvailabilityReply, CheckAvailabilityRequest
from services import reservations
from services.booking_rules import Rejection

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


# response_model_exclude_none: leave `reason` out entirely when there are times,
# so the model only ever sees fields that mean something.
@router.post(
    "/check-availability",
    response_model=CheckAvailabilityReply,
    response_model_exclude_none=True,
)
async def check_availability(
    session: DbSession, now: Now, body: CheckAvailabilityRequest
) -> CheckAvailabilityReply:
    """Which sittings on a date still have a table for the party."""
    slots = await reservations.get_availability(
        session, reservation_date=body.date, party_size=body.party_size, now=now
    )
    # "HH:MM", exactly what create_reservation accepts, so the model passes it
    # straight through instead of reformatting a spoken time.
    free = [s.start_time.strftime("%H:%M") for s in slots if s.available]
    if free:
        return CheckAvailabilityReply(available_times=free)

    reasons = [s.reason for s in slots if s.reason is not None]
    return CheckAvailabilityReply(available_times=[], reason=day_reason(reasons))
