from datetime import date

from fastapi import APIRouter

from api.v1.deps import DbSession, Now
from schemas.availability import SlotAvailabilityRead
from services import reservations
from services.reservations import SlotAvailability

router = APIRouter(tags=["availability"])


@router.get("/availability", response_model=list[SlotAvailabilityRead])
async def get_availability(
    session: DbSession, now: Now, date: date, party_size: int
) -> list[SlotAvailability]:
    """For each sitting on `date`: can a party of `party_size` be seated, and if not, why."""
    return await reservations.get_availability(
        session, reservation_date=date, party_size=party_size, now=now
    )
