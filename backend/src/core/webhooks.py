"""Verifying that a webhook really comes from ElevenLabs.

ElevenLabs signs every webhook with a secret shared when you create it:

    ElevenLabs-Signature: t=<unix seconds>,v0=<hex HMAC-SHA256 of "<t>.<raw body>">

Same scheme as their official SDK (`webhooks.construct_event`). The signature
covers the exact bytes received, so verify before parsing the JSON. The
timestamp stops someone replaying a captured webhook later.
"""

import hashlib
import hmac

from core.exceptions import UnauthorizedError

SIGNATURE_TOLERANCE_SECS = 30 * 60  # same as the SDK


def sign_elevenlabs(raw_body: bytes, secret: str, timestamp: int) -> str:
    """The header value ElevenLabs would send. Used to verify, and to sign in tests."""
    digest = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + raw_body, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v0={digest}"


def verify_elevenlabs_signature(
    raw_body: bytes, header: str | None, secret: str, *, now: float
) -> None:
    """Raise UnauthorizedError unless `header` is a valid, recent signature of `raw_body`."""
    if not header:
        raise UnauthorizedError("Missing webhook signature.")

    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    timestamp, signature = parts.get("t"), parts.get("v0")
    if not timestamp or not timestamp.isdigit() or not signature:
        raise UnauthorizedError("Malformed webhook signature.")

    if abs(now - int(timestamp)) > SIGNATURE_TOLERANCE_SECS:
        raise UnauthorizedError("Webhook signature expired.")

    expected = sign_elevenlabs(raw_body, secret, int(timestamp))
    # Constant time, so the signature can't be guessed by timing responses.
    if not hmac.compare_digest(f"t={timestamp},v0={signature}", expected):
        raise UnauthorizedError("Invalid webhook signature.")
