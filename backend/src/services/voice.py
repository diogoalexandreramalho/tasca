"""Conversation tokens for the website's "Talk to Tasca" button.

The agent is private (authentication on in ElevenLabs): a browser can only start a
conversation with a short-lived, single-use token. Only our API holds the ElevenLabs
key, so it fetches the token and hands it to the website. The audio then goes
straight between the browser and ElevenLabs (WebRTC); the agent calls our /agent
tools as on any other call. How many conversations a day are allowed, and how long
each may last, is enforced by ElevenLabs (the agent's call limits), not here.
"""

import httpx
from pydantic import BaseModel, ValidationError

from core.config import get_settings
from core.exceptions import ServiceUnavailableError
from core.logging import get_logger

TOKEN_PATH = "/v1/convai/conversation/token"

log = get_logger(__name__)


class _TokenReply(BaseModel):
    # ElevenLabs also returns the conversation_id; the website doesn't need it.
    token: str


async def create_conversation_token(http: httpx.AsyncClient) -> str:
    """Ask ElevenLabs for a WebRTC token for our agent. 503 if anything goes wrong."""
    settings = get_settings()
    if settings.elevenlabs_api_key is None or settings.elevenlabs_agent_id is None:
        log.warning("voice_session_not_configured")
        raise ServiceUnavailableError()

    try:
        res = await http.get(
            settings.elevenlabs_api_url + TOKEN_PATH,
            params={"agent_id": settings.elevenlabs_agent_id},
            headers={"xi-api-key": settings.elevenlabs_api_key},
        )
    except httpx.HTTPError as exc:
        log.warning("voice_session_upstream_unreachable", error=type(exc).__name__)
        raise ServiceUnavailableError() from exc

    if res.status_code != httpx.codes.OK:
        # Their error body says why (e.g. the key lacks a permission). It holds no
        # secrets, and it's the only clue when setting the key up, so log some of it.
        log.warning("voice_session_upstream_refused", status=res.status_code, body=res.text[:300])
        raise ServiceUnavailableError()

    try:
        reply = _TokenReply.model_validate_json(res.content)
    except ValidationError as exc:
        log.warning("voice_session_upstream_bad_reply")
        raise ServiceUnavailableError() from exc
    return reply.token
