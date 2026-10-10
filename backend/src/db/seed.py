"""Seed Tasca Tagarela's room and sittings.

Idempotent: safe to run repeatedly. Rows are matched on their natural key
(table name, slot start time) and updated to the values below.

    PYTHONPATH=src uv run python -m db.seed
"""

import asyncio
from datetime import time

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from core.logging import configure_logging, get_logger
from db.session import SessionLocal, engine
from models import BookingSlot, DiningTable, Service

# (name, min_capacity, max_capacity): 6x2, 6x4, 2x6, 1x8 = 15 tables, 56 seats.
TABLES: list[tuple[str, int, int]] = [
    *[(f"M{n}", 1, 2) for n in range(1, 7)],
    *[(f"M{n}", 2, 4) for n in range(7, 13)],
    *[(f"M{n}", 3, 6) for n in range(13, 15)],
    ("M15", 5, 8),
]

# Fixed 90-minute sittings, Lisbon local time.
SLOTS: list[tuple[Service, time, time]] = [
    (Service.LUNCH, time(12, 0), time(13, 30)),
    (Service.LUNCH, time(13, 30), time(15, 0)),
    (Service.DINNER, time(19, 0), time(20, 30)),
    (Service.DINNER, time(20, 30), time(22, 0)),
]


async def seed() -> None:
    async with SessionLocal() as session:
        tables_stmt = insert(DiningTable).values(
            [{"name": n, "min_capacity": lo, "max_capacity": hi} for n, lo, hi in TABLES]
        )
        await session.execute(
            tables_stmt.on_conflict_do_update(
                index_elements=[DiningTable.name],
                set_={
                    "min_capacity": tables_stmt.excluded.min_capacity,
                    "max_capacity": tables_stmt.excluded.max_capacity,
                    "updated_at": func.now(),
                },
            )
        )

        slots_stmt = insert(BookingSlot).values(
            [{"service": s, "start_time": start, "end_time": end} for s, start, end in SLOTS]
        )
        await session.execute(
            slots_stmt.on_conflict_do_update(
                index_elements=[BookingSlot.start_time],
                set_={
                    "service": slots_stmt.excluded.service,
                    "end_time": slots_stmt.excluded.end_time,
                    "updated_at": func.now(),
                },
            )
        )

        await session.commit()

    await engine.dispose()
    get_logger(__name__).info("seed_done", tables=len(TABLES), slots=len(SLOTS))


if __name__ == "__main__":
    configure_logging()
    asyncio.run(seed())
