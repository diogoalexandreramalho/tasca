import secrets

from core.config import get_settings
from core.exceptions import ForbiddenError, UnauthorizedError
from core.security import GUEST_SUBJECT, create_access_token, verify_password


def login(*, username: str, password: str) -> str:
    """Return an access token for the admin, or raise UnauthorizedError.

    The password hash is always verified, even when the username is wrong, so a
    wrong username and a wrong password take the same time to reject.
    """
    settings = get_settings()
    password_ok = verify_password(password, settings.admin_password_hash)
    username_ok = secrets.compare_digest(username.encode(), settings.admin_username.encode())
    if not (username_ok and password_ok):
        raise UnauthorizedError("Incorrect username or password.")
    return create_access_token(settings.admin_username)


def guest_login() -> str:
    """A read-only token for the guest demo. No password: guests can't change anything."""
    if not get_settings().guest_access_enabled:
        raise ForbiddenError("Guest access is turned off.")
    return create_access_token(GUEST_SUBJECT, role="guest")
