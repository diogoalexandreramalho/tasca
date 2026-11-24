"""POST /voice/session: the website's token for a conversation with the agent.

ElevenLabs is faked with httpx.MockTransport, so these tests never call it.
"""

from collections.abc import AsyncIterator, Callable, Iterator

import httpx
import pytest
from httpx import AsyncClient

from api.v1.deps import get_http_client
from core.config import get_settings
from main import app
from tests.conftest import TEST_ELEVENLABS_AGENT_ID, TEST_ELEVENLABS_API_KEY

URL = "/api/v1/voice/session"
Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
def fake_elevenlabs() -> Iterator[Callable[[Handler], list[httpx.Request]]]:
    """Route the app's outgoing HTTP to `handler`; returns the requests it received."""

    def install(handler: Handler) -> list[httpx.Request]:
        seen: list[httpx.Request] = []

        def record(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        async def fake_client() -> AsyncIterator[httpx.AsyncClient]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(record)) as c:
                yield c

        app.dependency_overrides[get_http_client] = fake_client
        return seen

    yield install
    app.dependency_overrides.pop(get_http_client, None)


async def test_returns_only_the_token_without_login(
    client: AsyncClient, fake_elevenlabs: Callable[[Handler], list[httpx.Request]]
) -> None:
    seen = fake_elevenlabs(
        lambda _: httpx.Response(200, json={"token": "tok_123", "conversation_id": "conv_1"})
    )

    res = await client.post(URL)

    assert res.status_code == 200
    assert res.json() == {"token": "tok_123"}
    assert res.headers["cache-control"] == "no-store"
    [req] = seen
    assert req.method == "GET"
    assert req.url.path == "/v1/convai/conversation/token"
    assert req.url.params["agent_id"] == TEST_ELEVENLABS_AGENT_ID
    assert req.headers["xi-api-key"] == TEST_ELEVENLABS_API_KEY


@pytest.mark.parametrize("missing", ["elevenlabs_api_key", "elevenlabs_agent_id"])
async def test_unconfigured_is_unavailable_without_calling_elevenlabs(
    client: AsyncClient,
    fake_elevenlabs: Callable[[Handler], list[httpx.Request]],
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    monkeypatch.setattr(get_settings(), missing, None)
    seen = fake_elevenlabs(lambda _: httpx.Response(200, json={"token": "tok_123"}))

    res = await client.post(URL)

    assert res.status_code == 503
    assert res.json()["code"] == "service_unavailable"
    assert seen == []


@pytest.mark.parametrize("status", [401, 403, 429, 500])
async def test_elevenlabs_refusing_is_unavailable_and_not_leaked(
    client: AsyncClient, fake_elevenlabs: Callable[[Handler], list[httpx.Request]], status: int
) -> None:
    fake_elevenlabs(
        lambda _: httpx.Response(status, json={"detail": {"message": "missing permission"}})
    )

    res = await client.post(URL)

    assert res.status_code == 503
    assert res.json()["code"] == "service_unavailable"
    assert "permission" not in res.text


async def test_elevenlabs_unreachable_is_unavailable(
    client: AsyncClient, fake_elevenlabs: Callable[[Handler], list[httpx.Request]]
) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    fake_elevenlabs(down)

    res = await client.post(URL)

    assert res.status_code == 503


@pytest.mark.parametrize("body", [b"{}", b"not json", b'{"token": null}'])
async def test_unexpected_reply_is_unavailable(
    client: AsyncClient, fake_elevenlabs: Callable[[Handler], list[httpx.Request]], body: bytes
) -> None:
    fake_elevenlabs(lambda _: httpx.Response(200, content=body))

    res = await client.post(URL)

    assert res.status_code == 503


async def test_only_post_is_allowed(client: AsyncClient) -> None:
    res = await client.get(URL)

    assert res.status_code == 405
