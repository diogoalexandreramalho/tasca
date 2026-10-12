import secrets

from core.config import get_settings
from core.exceptions import UnauthorizedError
from core.security import create_access_token, verify_password


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
