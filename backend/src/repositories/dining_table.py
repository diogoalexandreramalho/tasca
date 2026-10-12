from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import DiningTable


async def list_all(session: AsyncSession) -> Sequence[DiningTable]:
    result = await session.execute(select(DiningTable).order_by(DiningTable.id))
    return result.scalars().all()


async def list_active(session: AsyncSession) -> Sequence[DiningTable]:
    result = await session.execute(
        select(DiningTable).where(DiningTable.is_active).order_by(DiningTable.id)
    )
    return result.scalars().all()
