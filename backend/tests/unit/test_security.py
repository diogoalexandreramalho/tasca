from datetime import timedelta

import jwt
import pytest

from core.security import create_access_token, decode_token, hash_password, verify_password
from services.auth import login
from tests.conftest import TEST_ADMIN_PASSWORD, TEST_ADMIN_USERNAME


def test_password_hash_round_trip() -> None:
    hashed = hash_password("s3cret-passphrase")

    assert hashed.startswith("$argon2id$")
    assert verify_password("s3cret-passphrase", hashed)
    assert not verify_password("wrong", hashed)


def test_token_round_trip() -> None:
    assert decode_token(create_access_token("admin"))["sub"] == "admin"


def test_expired_token_is_rejected() -> None:
    token = create_access_token("admin", expires_delta=timedelta(seconds=-1))

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_token_signed_with_another_key_is_rejected() -> None:
    forged = jwt.encode({"sub": "admin"}, "some-other-key-that-is-32-chars-long!", "HS256")

    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(forged)


def test_login_with_the_admin_credentials_returns_a_token() -> None:
    token = login(username=TEST_ADMIN_USERNAME, password=TEST_ADMIN_PASSWORD)

    assert decode_token(token)["sub"] == TEST_ADMIN_USERNAME
