import pytest
from pwdlib import PasswordHash
from pydantic import ValidationError

from core.config import Settings


def _build(cors: object) -> Settings:
    # Required fields (secret, admin hash) come from the env set in tests/conftest.py.
    return Settings(cors_origins=cors)  # type: ignore[arg-type,call-arg]


def test_cors_origins_comma_separated_string() -> None:
    assert _build("http://a,http://b").cors_origins == ["http://a", "http://b"]


def test_cors_origins_trims_whitespace_and_empty_segments() -> None:
    assert _build("http://a, ,http://b").cors_origins == ["http://a", "http://b"]


def test_cors_origins_passthrough_for_list() -> None:
    assert _build(["http://a", "http://b"]).cors_origins == ["http://a", "http://b"]


def test_accepts_a_real_argon2_hash() -> None:
    hashed = PasswordHash.recommended().hash("a-password")

    assert Settings(admin_password_hash=hashed).admin_password_hash == hashed  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "bad_hash",
    [
        "not-a-hash",
        # What an unquoted hash can turn into once `$...` gets expanded.
        "=19=65536,t=3,p=4=abc",
        # The hash with its `$argon2id$v=19$` prefix cut off.
        "m=65536,t=3,p=4$Wskr6wfrhK89NJEK8bL5fg$cSnh8BPgjTSOhEgQ4kEYNsnZfSo3GOOnCmMV3OO/exg",
    ],
)
def test_rejects_a_malformed_hash_at_startup(bad_hash: str) -> None:
    with pytest.raises(ValidationError, match="ADMIN_PASSWORD_HASH is not a valid argon2 hash"):
        Settings(admin_password_hash=bad_hash)  # type: ignore[call-arg]
