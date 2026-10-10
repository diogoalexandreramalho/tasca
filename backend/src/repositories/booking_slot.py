from collections.abc import Sequence
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import BookingSlot


async def list_all(session: AsyncSession) -> Sequence[BookingSlot]:
    result = await session.execute(select(BookingSlot).order_by(BookingSlot.start_time))
    return result.scalars().all()


async def get_by_start_time(session: AsyncSession, start_time: time) -> BookingSlot | None:
    result = await session.execute(select(BookingSlot).where(BookingSlot.start_time == start_time))
    return result.scalar_one_or_none()
