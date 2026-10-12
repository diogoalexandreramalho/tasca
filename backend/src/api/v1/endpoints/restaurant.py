from collections.abc import Sequence

from fastapi import APIRouter

from api.v1.deps import DbSession
from models import BookingSlot, DiningTable
from schemas.booking_slot import BookingSlotRead
from schemas.dining_table import DiningTableRead
from services import restaurant

router = APIRouter(tags=["restaurant"])


@router.get("/slots", response_model=list[BookingSlotRead])
async def list_slots(session: DbSession) -> Sequence[BookingSlot]:
    """The fixed sittings, in start-time order."""
    return await restaurant.list_slots(session)


@router.get("/tables", response_model=list[DiningTableRead])
async def list_tables(session: DbSession) -> Sequence[DiningTable]:
    """Every table in the room, including inactive ones."""
    return await restaurant.list_tables(session)
