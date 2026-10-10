from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Customer


async def get_by_phone(session: AsyncSession, phone: str) -> Customer | None:
    result = await session.execute(select(Customer).where(Customer.phone == phone))
    return result.scalar_one_or_none()


async def upsert(session: AsyncSession, *, name: str, phone: str) -> Customer:
    """Create the customer, or update the name of the existing one with this phone.

    A single statement, so two calls from the same number can't create duplicates.
    """
    insert_stmt = insert(Customer).values(name=name, phone=phone)
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[Customer.phone],
        set_={"name": insert_stmt.excluded.name, "updated_at": func.now()},
    ).returning(Customer)
    result = await session.execute(upsert_stmt, execution_options={"populate_existing": True})
    customer: Customer = result.scalar_one()
    return customer
