"""The read-only guest session ("Explore as a guest" on the dashboard)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from httpx import AsyncClient

from core.config import get_settings
from tests.integration.webhook_helpers import agent_book, payload, send

FRIDAY = "2026-10-16"
BOOKING: dict[str, Any] = {
    "reservation_date": FRIDAY,
    "start_time": "20:30",
    "party_size": 2,
    "customer_name": "Ana Silva",
    "phone": "912 345 678",
    "notes": "Allergy: nuts. Call 912 345 678 if late.",
}


async def book(api_client: AsyncClient) -> dict[str, Any]:
    response = await api_client.post("/api/v1/reservations", json=BOOKING)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


class TestGuestLogin:
    async def test_needs_no_password_and_gives_a_bearer_token(
        self, anon_client: AsyncClient
    ) -> None:
        response = await anon_client.post("/api/v1/auth/guest")

        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0
        me = await anon_client.get(
            "/api/v1/slots", headers={"Authorization": f"Bearer {body['access_token']}"}
        )
        assert me.status_code == 200

    async def test_can_be_turned_off(
        self, anon_client: AsyncClient, guest_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(get_settings(), "guest_access_enabled", False)

        login = await anon_client.post("/api/v1/auth/guest")
        existing = await guest_client.get("/api/v1/slots")

        assert login.status_code == 403
        assert existing.status_code == 401  # tokens already handed out stop working


class TestGuestCanRead:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/slots",
            "/api/v1/tables",
            f"/api/v1/availability?date={FRIDAY}&party_size=2",
            f"/api/v1/reservations?date={FRIDAY}",
            "/api/v1/reservations?name=ana",
            "/api/v1/calls",
        ],
    )
    async def test_dashboard_pages(self, guest_client: AsyncClient, path: str) -> None:
        response = await guest_client.get(path)

        assert response.status_code == 200, response.text


class TestGuestCantChange:
    async def test_creating_is_forbidden_and_books_nothing(
        self, api_client: AsyncClient, guest_client: AsyncClient
    ) -> None:
        response = await guest_client.post("/api/v1/reservations", json=BOOKING)

        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"
        day = await api_client.get("/api/v1/reservations", params={"date": FRIDAY})
        assert day.json() == []

    async def test_cancelling_is_forbidden_and_keeps_the_booking(
        self, api_client: AsyncClient, guest_client: AsyncClient
    ) -> None:
        booking = await book(api_client)

        response = await guest_client.post(f"/api/v1/reservations/{booking['id']}/cancel")

        assert response.status_code == 403
        still = await api_client.get(f"/api/v1/reservations/{booking['id']}")
        assert still.json()["status"] == "confirmed"

    async def test_searching_by_phone_is_forbidden(self, guest_client: AsyncClient) -> None:
        response = await guest_client.get("/api/v1/reservations", params={"phone": "912345678"})

        assert response.status_code == 403


class TestGuestSeesPhonesMasked:
    async def test_in_the_day_view_search_and_single_booking(
        self, api_client: AsyncClient, guest_client: AsyncClient
    ) -> None:
        booking = await book(api_client)

        [day] = (await guest_client.get("/api/v1/reservations", params={"date": FRIDAY})).json()
        [found] = (await guest_client.get("/api/v1/reservations", params={"name": "ana"})).json()
        single = (await guest_client.get(f"/api/v1/reservations/{booking['id']}")).json()

        for seen in (day, found, single):
            assert seen["customer"]["phone"] == "+351•••••••78"
            assert seen["notes"] == "Allergy: nuts. Call ••• ••• ••• if late."
            assert seen["customer"]["name"] == "Ana Silva"  # names stay

    async def test_the_admin_still_sees_everything(self, api_client: AsyncClient) -> None:
        await book(api_client)

        [day] = (await api_client.get("/api/v1/reservations", params={"date": FRIDAY})).json()

        assert day["customer"]["phone"] == "+351912345678"
        assert day["notes"] == BOOKING["notes"]

    async def test_in_call_summaries_and_transcripts_but_not_times(
        self, anon_client: AsyncClient, agent_client: AsyncClient, guest_client: AsyncClient
    ) -> None:
        await agent_book(agent_client, "conv_guest")
        body = payload("conv_guest", summary="Ana booked 20:30 Friday; phone 912 345 678.")
        body["data"]["transcript"].append(
            {"role": "user", "message": "It's 912 345 678, at 20:30.", "time_in_call_secs": 9}
        )
        await send(anon_client, body)

        [listed] = (await guest_client.get("/api/v1/calls")).json()
        detail = (await guest_client.get("/api/v1/calls/by-conversation/conv_guest")).json()

        assert listed["summary"] == "Ana booked 20:30 Friday; phone ••• ••• •••."
        assert detail["summary"] == listed["summary"]
        assert detail["transcript"][-1]["message"] == "It's ••• ••• •••, at 20:30."
        assert detail["bookings"][0]["customer_name"] == "Ana"


class TestTokens:
    async def test_a_guest_token_is_not_an_admin_token(
        self, anon_client: AsyncClient, guest_client: AsyncClient
    ) -> None:
        # Same endpoint, two roles: only the admin may write.
        response = await guest_client.post(
            "/api/v1/reservations/00000000-0000-0000-0000-000000000000/cancel"
        )

        assert response.status_code == 403  # not 404: refused before looking anything up

    async def test_admin_tokens_from_before_roles_still_work(
        self, anon_client: AsyncClient
    ) -> None:
        settings = get_settings()
        old = jwt.encode(
            {"sub": settings.admin_username, "exp": datetime.now(UTC) + timedelta(hours=1)},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await anon_client.post(
            "/api/v1/reservations", json=BOOKING, headers={"Authorization": f"Bearer {old}"}
        )

        assert response.status_code == 201

    async def test_no_token_is_still_401(self, anon_client: AsyncClient) -> None:
        response = await anon_client.get(f"/api/v1/reservations?date={FRIDAY}")

        assert response.status_code == 401
