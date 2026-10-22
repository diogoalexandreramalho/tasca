import os
from collections.abc import AsyncIterator

from pwdlib import PasswordHash

# Test credentials, set before anything reads settings (they're cached on first use).
# Always overwrite: CI and local shells may already define these (CI sets placeholders
# for `alembic upgrade`), and tests must use credentials they know.
TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "correct-horse-battery"
TEST_AGENT_SECRET = "test-agent-secret-that-is-at-least-32-chars"
os.environ["AGENT_API_SECRET"] = TEST_AGENT_SECRET
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars"
os.environ["ADMIN_USERNAME"] = TEST_ADMIN_USERNAME
os.environ["ADMIN_PASSWORD_HASH"] = PasswordHash.recommended().hash(TEST_ADMIN_PASSWORD)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
