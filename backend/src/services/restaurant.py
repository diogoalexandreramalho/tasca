"""Read-only reference data: the room's tables and the sittings."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from models import BookingSlot, DiningTable
from repositories import booking_slot as slot_repo
from repositories import dining_table as table_repo


async def list_slots(session: AsyncSession) -> Sequence[BookingSlot]:
    return await slot_repo.list_all(session)


async def list_tables(session: AsyncSession) -> Sequence[DiningTable]:
    return await table_repo.list_all(session)
