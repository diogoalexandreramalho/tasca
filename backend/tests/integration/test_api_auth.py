from datetime import timedelta

import pytest
from httpx import AsyncClient

from core.security import create_access_token
from tests.conftest import TEST_ADMIN_PASSWORD, TEST_ADMIN_USERNAME

PROTECTED = [
    ("GET", "/api/v1/slots"),
    ("GET", "/api/v1/tables"),
    ("GET", "/api/v1/availability?date=2026-10-16&party_size=2"),
    ("GET", "/api/v1/reservations?date=2026-10-16"),
    ("GET", "/api/v1/reservations/00000000-0000-0000-0000-000000000000"),
    ("POST", "/api/v1/reservations"),
    ("POST", "/api/v1/reservations/00000000-0000-0000-0000-000000000000/cancel"),
]


async def login(client: AsyncClient, username: str, password: str) -> tuple[int, dict[str, object]]:
    response = await client.post(
        "/api/v1/auth/token", data={"username": username, "password": password}
    )
    body: dict[str, object] = response.json()
    return response.status_code, body


class TestLogin:
    async def test_correct_credentials_return_a_working_token(
        self, anon_client: AsyncClient
    ) -> None:
        status, body = await login(anon_client, TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)

        assert status == 200
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 12 * 60 * 60
        response = await anon_client.get(
            "/api/v1/slots", headers={"Authorization": f"Bearer {body['access_token']}"}
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        ("username", "password"),
        [
            (TEST_ADMIN_USERNAME, "wrong-password"),
            ("someone-else", TEST_ADMIN_PASSWORD),
        ],
    )
    async def test_wrong_credentials_get_the_same_401(
        self, anon_client: AsyncClient, username: str, password: str
    ) -> None:
        status, body = await login(anon_client, username, password)

        assert status == 401
        assert body["code"] == "unauthorized"
        assert body["message"] == "Incorrect username or password."

    async def test_missing_fields_are_422(self, anon_client: AsyncClient) -> None:
        status, body = await login(anon_client, "", "")

        assert status == 422
        assert {e["field"] for e in body["details"]["errors"]} == {"username", "password"}  # type: ignore[index]


class TestProtectedEndpoints:
    @pytest.mark.parametrize(("method", "path"), PROTECTED)
    async def test_require_a_token(self, anon_client: AsyncClient, method: str, path: str) -> None:
        response = await anon_client.request(method, path)

        assert response.status_code == 401
        assert response.json()["code"] == "unauthorized"
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.parametrize(
        "token",
        [
            "not-a-jwt",
            create_access_token(TEST_ADMIN_USERNAME, expires_delta=timedelta(seconds=-1)),
            create_access_token("someone-else"),
        ],
        ids=["garbage", "expired", "wrong-subject"],
    )
    async def test_reject_bad_tokens(self, anon_client: AsyncClient, token: str) -> None:
        response = await anon_client.get(
            "/api/v1/slots", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401
        assert response.json()["message"] == "Invalid or expired token."

    async def test_health_stays_public(self, anon_client: AsyncClient) -> None:
        response = await anon_client.get("/api/v1/health")

        assert response.status_code == 200
