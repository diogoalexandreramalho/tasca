import os
from collections.abc import AsyncIterator

from pwdlib import PasswordHash

# Test credentials, set before anything reads settings (they're cached on first use).
TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "correct-horse-battery"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-chars")
os.environ.setdefault("ADMIN_USERNAME", TEST_ADMIN_USERNAME)
os.environ.setdefault("ADMIN_PASSWORD_HASH", PasswordHash.recommended().hash(TEST_ADMIN_PASSWORD))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
