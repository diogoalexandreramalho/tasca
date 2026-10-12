from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import UnauthorizedError
from core.security import decode_token
from db.session import get_session

DbSession = Annotated[AsyncSession, Depends(get_session)]


def get_now() -> datetime:
    """The current time. A dependency so tests can pin it (see `app.dependency_overrides`)."""
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(get_now)]


# auto_error=False so a missing token goes through our UnauthorizedError (standard
# error shape) instead of FastAPI's own 401.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def require_admin(token: Annotated[str | None, Depends(oauth2_scheme)]) -> str:
    """Reject the request unless it carries a valid, unexpired admin token."""
    if token is None:
        raise UnauthorizedError()
    try:
        subject = decode_token(token).get("sub")
    except InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc
    admin_username = get_settings().admin_username
    if subject != admin_username:
        raise UnauthorizedError("Invalid or expired token.")
    return admin_username


CurrentAdmin = Annotated[str, Depends(require_admin)]
