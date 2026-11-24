import os
from collections.abc import AsyncIterator

from pwdlib import PasswordHash

# Test credentials, set before anything reads settings (they're cached on first use).
# Always overwrite: CI and local shells may already define these (CI sets placeholders
# for `alembic upgrade`), and tests must use credentials they know.
TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "correct-horse-battery"
TEST_AGENT_SECRET = "test-agent-secret-that-is-at-least-32-chars"
TEST_WEBHOOK_SECRET = "wsec_test_webhook_secret"
TEST_ELEVENLABS_API_KEY = "test-elevenlabs-api-key"
TEST_ELEVENLABS_AGENT_ID = "agent_test"
os.environ["AGENT_API_SECRET"] = TEST_AGENT_SECRET
os.environ["ELEVENLABS_WEBHOOK_SECRET"] = TEST_WEBHOOK_SECRET
os.environ["ELEVENLABS_API_KEY"] = TEST_ELEVENLABS_API_KEY
os.environ["ELEVENLABS_AGENT_ID"] = TEST_ELEVENLABS_AGENT_ID
# Tests never reach the real ElevenLabs: they fake it (see test_api_voice.py).
os.environ["ELEVENLABS_API_URL"] = "https://elevenlabs.test"
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
