import pytest

from core.exceptions import UnauthorizedError
from core.webhooks import sign_elevenlabs, verify_elevenlabs_signature

SECRET = "wsec_test"
BODY = b'{"type":"post_call_transcription","data":{}}'
NOW = 1_800_000_000


def verify(body: bytes, header: str | None, secret: str = SECRET, now: float = NOW) -> None:
    verify_elevenlabs_signature(body, header, secret, now=now)


def test_accepts_a_valid_signature() -> None:
    verify(BODY, sign_elevenlabs(BODY, SECRET, NOW))


def test_accepts_slight_clock_skew_within_tolerance() -> None:
    verify(BODY, sign_elevenlabs(BODY, SECRET, NOW - 29 * 60))


@pytest.mark.parametrize(
    ("body", "header", "message"),
    [
        (BODY, None, "Missing webhook signature."),
        (BODY, "", "Missing webhook signature."),
        (BODY, "v0=abc", "Malformed webhook signature."),
        (BODY, f"t={NOW}", "Malformed webhook signature."),
        (BODY, "t=yesterday,v0=abc", "Malformed webhook signature."),
        # Signed with another secret.
        (BODY, sign_elevenlabs(BODY, "someone-else", NOW), "Invalid webhook signature."),
        # Body changed after signing.
        (BODY + b" ", sign_elevenlabs(BODY, SECRET, NOW), "Invalid webhook signature."),
        # A valid signature from 31 minutes ago (replayed).
        (BODY, sign_elevenlabs(BODY, SECRET, NOW - 31 * 60), "Webhook signature expired."),
    ],
)
def test_rejects(body: bytes, header: str | None, message: str) -> None:
    with pytest.raises(UnauthorizedError, match=message):
        verify(body, header)
