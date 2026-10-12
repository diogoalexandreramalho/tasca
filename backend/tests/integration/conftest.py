"""Integration tests run against a real Postgres in a separate `tasca_test` database.

The database is created if missing and migrated from scratch once per run (which
also exercises the migrations). Each test starts from freshly seeded tables.
"""

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.deps import get_now
from core.security import create_access_token
from db.seed import seed
from db.session import get_session
from main import app
from services.booking_rules import RESTAURANT_TZ
from tests.conftest import TEST_ADMIN_USERNAME

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://tasca:tasca@localhost:5432/tasca_test"
)


@pytest.fixture(scope="session")
def database_url() -> str:
    sync_url = make_url(TEST_DATABASE_URL).set(drivername="postgresql+psycopg")

    admin = create_engine(sync_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": sync_url.database}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{sync_url.database}"'))
    admin.dispose()

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", sync_url.render_as_string(hide_password=False))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return TEST_DATABASE_URL


@pytest.fixture
async def session_factory(database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE reservations, customers, dining_tables, booking_slots "
                "RESTART IDENTITY CASCADE"
            )
        )
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        await seed(session)
    yield factory
    await engine.dispose()


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s


@dataclass
class Clock:
    now: datetime


@pytest.fixture
def clock() -> Clock:
    """What the API thinks "now" is. Tests can move it: `clock.now = ...`."""
    return Clock(now=datetime(2026, 10, 14, 10, 0, tzinfo=RESTAURANT_TZ))  # Wednesday


@pytest.fixture
async def anon_client(
    session_factory: async_sessionmaker[AsyncSession], clock: Clock
) -> AsyncIterator[AsyncClient]:
    """HTTP client for the real app, wired to the test database and the test clock. No token."""

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = test_session
    app.dependency_overrides[get_now] = lambda: clock.now
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def api_client(anon_client: AsyncClient) -> AsyncClient:
    """Same as `anon_client`, logged in as the admin."""
    anon_client.headers["Authorization"] = f"Bearer {create_access_token(TEST_ADMIN_USERNAME)}"
    return anon_client
