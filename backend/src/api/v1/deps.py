import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import ForbiddenError, UnauthorizedError
from core.security import GUEST_SUBJECT, Role, decode_token
from db.session import get_session

DbSession = Annotated[AsyncSession, Depends(get_session)]


def get_now() -> datetime:
    """The current time. A dependency so tests can pin it (see `app.dependency_overrides`)."""
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(get_now)]


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client for calls to other services. A dependency so tests can fake them."""
    async with httpx.AsyncClient(timeout=10) as client:
        yield client


HttpClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]


# auto_error=False so a missing token goes through our UnauthorizedError (standard
# error shape) instead of FastAPI's own 401.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


@dataclass(frozen=True)
class Viewer:
    """Who is looking at the dashboard: the admin, or a read-only guest (the demo)."""

    role: Role

    @property
    def is_guest(self) -> bool:
        return self.role == "guest"


def require_viewer(token: Annotated[str | None, Depends(oauth2_scheme)]) -> Viewer:
    """Reject the request unless it carries a valid, unexpired admin or guest token."""
    if token is None:
        raise UnauthorizedError()
    try:
        claims = decode_token(token)
    except InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc
    settings = get_settings()
    subject, role = claims.get("sub"), claims.get("role", "admin")  # older tokens: admin
    if role == "admin" and subject == settings.admin_username:
        return Viewer(role="admin")
    if role == "guest" and subject == GUEST_SUBJECT and settings.guest_access_enabled:
        return Viewer(role="guest")
    raise UnauthorizedError("Invalid or expired token.")


CurrentViewer = Annotated[Viewer, Depends(require_viewer)]


def require_admin(viewer: CurrentViewer) -> None:
    """Changes are for the admin only: guests get 403 (they're logged in, just not allowed)."""
    if viewer.is_guest:
        raise ForbiddenError("The demo is read-only.")


def require_agent(x_agent_secret: Annotated[str | None, Header()] = None) -> None:
    """Reject the request unless it carries the voice agent's shared secret.

    The agent is a machine, not a person: instead of logging in it sends a fixed
    secret on every call (configured once in ElevenLabs). `compare_digest` takes
    the same time whether the first or the last character differs, so the secret
    can't be guessed one character at a time by timing responses.
    """
    expected = get_settings().agent_api_secret
    if expected is None or x_agent_secret is None:
        raise UnauthorizedError()
    if not secrets.compare_digest(x_agent_secret.encode(), expected.encode()):
        raise UnauthorizedError("Invalid agent secret.")
