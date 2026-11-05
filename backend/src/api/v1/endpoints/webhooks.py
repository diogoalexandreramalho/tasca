"""Webhooks ElevenLabs sends us (no login: each one is signed instead).

Configure in ElevenLabs as the post-call webhook, with "transcript" events:
    POST /api/v1/webhooks/elevenlabs/post-call
"""

import time
from typing import Annotated

from fastapi import APIRouter, Header, Request
from pydantic import ValidationError

from api.v1.deps import DbSession, Now
from core.config import get_settings
from core.exceptions import UnauthorizedError, ValidationAppError
from core.logging import get_logger
from core.webhooks import verify_elevenlabs_signature
from schemas.webhooks import PostCallTranscription, WebhookAck, WebhookEnvelope
from services import calls

router = APIRouter(prefix="/webhooks/elevenlabs", tags=["webhooks"])
log = get_logger(__name__)


@router.post("/post-call", response_model=WebhookAck)
async def post_call(
    request: Request,
    session: DbSession,
    now: Now,
    elevenlabs_signature: Annotated[str | None, Header()] = None,
) -> WebhookAck:
    """Record a finished conversation in the call log."""
    secret = get_settings().elevenlabs_webhook_secret
    if secret is None:
        raise UnauthorizedError("Webhook secret not configured.")

    # The signature covers the exact bytes sent: verify before parsing anything.
    # Real time here, not the injectable `now`: it's about the message's age.
    raw = await request.body()
    verify_elevenlabs_signature(raw, elevenlabs_signature, secret, now=time.time())

    try:
        envelope = WebhookEnvelope.model_validate_json(raw)
    except ValidationError as exc:
        raise ValidationAppError("Unrecognised webhook payload.") from exc

    # Audio and call-initiation-failure events aren't used. Answer 200 so ElevenLabs
    # doesn't keep retrying them.
    if envelope.type != "post_call_transcription":
        log.info("webhook_ignored", type=envelope.type)
        return WebhookAck(status="ignored")

    try:
        data = PostCallTranscription.model_validate(envelope.data)
    except ValidationError as exc:
        raise ValidationAppError("Unrecognised post-call transcription.") from exc

    call = await calls.record_call(session, data, now=now)
    log.info("call_recorded", conversation_id=call.conversation_id, outcome=call.outcome)
    return WebhookAck(status="recorded")
