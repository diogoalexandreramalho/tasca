"""The voice agent's tools, called over HTTP like ElevenLabs does."""

from typing import Any

import pytest
from httpx import AsyncClient

from core.security import create_access_token
from tests.conftest import TEST_ADMIN_USERNAME

# The test clock is Wednesday 14 Oct 2026, 10:00 Lisbon (see conftest).
FRIDAY, MONDAY = "2026-10-16", "2026-10-19"


async def check(client: AsyncClient, date: str, party_size: int) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/agent/check-availability", json={"date": date, "party_size": party_size}
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


class TestAgentAuth:
    async def test_requires_the_secret(self, anon_client: AsyncClient) -> None:
        response = await anon_client.post(
            "/api/v1/agent/check-availability", json={"date": FRIDAY, "party_size": 2}
        )

        assert response.status_code == 401

    async def test_rejects_a_wrong_secret(self, anon_client: AsyncClient) -> None:
        response = await anon_client.post(
            "/api/v1/agent/check-availability",
            json={"date": FRIDAY, "party_size": 2},
            headers={"X-Agent-Secret": "x" * 40},
        )

        assert response.status_code == 401
        assert response.json()["message"] == "Invalid agent secret."

    async def test_an_admin_token_is_not_enough(self, anon_client: AsyncClient) -> None:
        # Separate credentials on purpose: the agent never holds the admin password,
        # and the dashboard's token can't be used to act as the agent.
        response = await anon_client.post(
            "/api/v1/agent/check-availability",
            json={"date": FRIDAY, "party_size": 2},
            headers={"Authorization": f"Bearer {create_access_token(TEST_ADMIN_USERNAME)}"},
        )

        assert response.status_code == 401


class TestCheckAvailability:
    async def test_lists_only_the_free_start_times(self, agent_client: AsyncClient) -> None:
        body = await check(agent_client, FRIDAY, 4)

        # Nothing else: no echo of the request, no end times, no `reason` key.
        assert body == {"available_times": ["12:00", "13:30", "19:00", "20:30"]}

    async def test_full_sitting_is_left_out(
        self, agent_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        # Only M15 fits 8 people; book it at 20:30 through the dashboard API.
        response = await api_client.post(
            "/api/v1/reservations",
            json={
                "reservation_date": FRIDAY,
                "start_time": "20:30",
                "party_size": 8,
                "customer_name": "Festa",
                "phone": "912345678",
            },
        )
        assert response.status_code == 201

        body = await check(agent_client, FRIDAY, 8)

        assert body == {"available_times": ["12:00", "13:30", "19:00"]}

    @pytest.mark.parametrize(
        ("date", "party_size", "reason"),
        [
            (MONDAY, 2, "closed_day"),
            (FRIDAY, 9, "party_size_out_of_range"),
            ("2026-10-13", 2, "in_the_past"),
            ("2027-01-05", 2, "too_far_ahead"),
        ],
    )
    async def test_nothing_available_comes_with_one_reason(
        self, agent_client: AsyncClient, date: str, party_size: int, reason: str
    ) -> None:
        body = await check(agent_client, date, party_size)

        assert body == {"available_times": [], "reason": reason}

    async def test_malformed_input_is_a_422(self, agent_client: AsyncClient) -> None:
        # A misconfigured tool (wrong date format), not something to say to the caller.
        response = await agent_client.post(
            "/api/v1/agent/check-availability", json={"date": "sexta-feira", "party_size": 2}
        )

        assert response.status_code == 422
        assert response.json()["details"]["errors"][0]["field"] == "date"
