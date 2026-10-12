"""Print an ADMIN_PASSWORD_HASH line for backend/.env.

    PYTHONPATH=src uv run python -m core.hash_password

The password is read without echoing and never stored; only its argon2id hash is.
"""

import sys
from getpass import getpass

from pwdlib import PasswordHash

MIN_LENGTH = 12


def main() -> int:
    password = getpass("Admin password: ")
    if len(password) < MIN_LENGTH:
        print(f"Use at least {MIN_LENGTH} characters.", file=sys.stderr)
        return 1
    if getpass("Repeat password: ") != password:
        print("Passwords don't match.", file=sys.stderr)
        return 1

    hashed = PasswordHash.recommended().hash(password)
    # Single quotes stop both python-dotenv and docker compose from expanding the `$`s.
    print(f"\nADMIN_PASSWORD_HASH='{hashed}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
