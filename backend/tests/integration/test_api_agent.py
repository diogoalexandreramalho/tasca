"""The voice agent's tools, called over HTTP like ElevenLabs does."""

from datetime import datetime
from typing import Any

import pytest
from httpx import AsyncClient

from core.security import create_access_token
from services.booking_rules import RESTAURANT_TZ
from tests.conftest import TEST_ADMIN_USERNAME
from tests.integration.conftest import Clock

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


def booking(**overrides: Any) -> dict[str, Any]:
    return {
        "date": FRIDAY,
        "time": "20:30",
        "party_size": 2,
        "name": "Ana Silva",
        "phone": "912 345 678",
        "notes": None,
    } | overrides


async def create(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/agent/create-reservation", json=booking(**overrides))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def day_view(client: AsyncClient, date: str) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/reservations", params={"date": date})
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] = response.json()
    return body


class TestCreateReservation:
    async def test_books_and_shows_up_in_the_dashboard(
        self, agent_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        body = await create(agent_client, notes="Alergia: marisco")

        assert body == {"status": "booked"}
        [r] = await day_view(api_client, FRIDAY)
        assert r["customer"] == {
            "id": r["customer"]["id"],
            "name": "Ana Silva",
            "phone": "+351912345678",
        }
        assert r["booking_slot"]["start_time"] == "20:30:00"
        assert r["notes"] == "Alergia: marisco"

    async def test_a_retry_does_not_book_twice(
        self, agent_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        assert await create(agent_client) == {"status": "booked"}
        # Same booking again, phone written differently.
        assert await create(agent_client, phone="+351 912345678") == {"status": "already_booked"}

        assert len(await day_view(api_client, FRIDAY)) == 1

    async def test_same_phone_can_book_another_sitting(self, agent_client: AsyncClient) -> None:
        assert await create(agent_client, time="20:30") == {"status": "booked"}
        assert await create(agent_client, time="12:00") == {"status": "booked"}

    async def test_closed_day_is_rejected_without_alternatives(
        self, agent_client: AsyncClient
    ) -> None:
        body = await create(agent_client, date=MONDAY)

        assert body == {"status": "rejected", "reason": "closed_day"}

    async def test_fully_booked_offers_the_remaining_times(self, agent_client: AsyncClient) -> None:
        # Only M15 fits 8 people.
        assert await create(agent_client, party_size=8, phone="910000001") == {"status": "booked"}

        body = await create(agent_client, party_size=8, phone="910000002")

        assert body == {
            "status": "rejected",
            "reason": "fully_booked",
            "available_times": ["12:00", "13:30", "19:00"],
        }

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"phone": "12345"}, "phone"),
            ({"name": "   "}, "name"),
            ({"time": "21:00"}, "time"),  # a valid time, but not a sitting
            ({"time": "8:30 PM"}, "time"),  # not "HH:MM"
        ],
    )
    async def test_bad_input_asks_for_the_field_again(
        self,
        agent_client: AsyncClient,
        api_client: AsyncClient,
        overrides: dict[str, str],
        field: str,
    ) -> None:
        body = await create(agent_client, **overrides)

        assert body == {"status": "invalid", "field": field}
        assert await day_view(api_client, FRIDAY) == []

    async def test_requires_the_secret(self, anon_client: AsyncClient) -> None:
        response = await anon_client.post("/api/v1/agent/create-reservation", json=booking())

        assert response.status_code == 401


async def find(client: AsyncClient, **body: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/agent/find-reservations", json=body)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


async def cancel(client: AsyncClient, reservation_id: str, phone: str) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/agent/cancel-reservation",
        json={"reservation_id": reservation_id, "phone": phone},
    )
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


class TestFindReservations:
    async def test_lists_only_this_phones_upcoming_bookings(
        self, agent_client: AsyncClient
    ) -> None:
        await create(agent_client, date="2026-10-17", time="13:30", party_size=3)
        await create(agent_client, date=FRIDAY, time="20:30", party_size=2)
        await create(agent_client, phone="910000009", name="Rui Costa")  # someone else

        body = await find(agent_client, phone="+351 912 345 678")

        # Soonest first; only id, date, time, party size and name.
        assert [
            {k: r[k] for k in ("date", "time", "party_size", "name")} for r in body["reservations"]
        ] == [
            {"date": FRIDAY, "time": "20:30", "party_size": 2, "name": "Ana Silva"},
            {"date": "2026-10-17", "time": "13:30", "party_size": 3, "name": "Ana Silva"},
        ]
        assert set(body["reservations"][0]) == {"id", "date", "time", "party_size", "name"}
        assert "field" not in body

    async def test_can_narrow_to_one_day(self, agent_client: AsyncClient) -> None:
        await create(agent_client, date="2026-10-17", time="13:30")
        await create(agent_client, date=FRIDAY, time="20:30")

        body = await find(agent_client, phone="912345678", date="2026-10-17")

        assert [r["date"] for r in body["reservations"]] == ["2026-10-17"]

    async def test_skips_sittings_that_already_started(
        self, agent_client: AsyncClient, clock: Clock
    ) -> None:
        await create(agent_client, date=FRIDAY, time="12:00")
        await create(agent_client, date=FRIDAY, time="20:30")
        clock.now = datetime(2026, 10, 16, 13, 0, tzinfo=RESTAURANT_TZ)  # Friday after lunch

        body = await find(agent_client, phone="912345678")

        assert [r["time"] for r in body["reservations"]] == ["20:30"]

    async def test_nothing_found_is_an_empty_list(self, agent_client: AsyncClient) -> None:
        assert await find(agent_client, phone="919999999") == {"reservations": []}

    async def test_invalid_phone_asks_for_it_again(self, agent_client: AsyncClient) -> None:
        assert await find(agent_client, phone="12345") == {"reservations": [], "field": "phone"}

    async def test_requires_the_secret(self, anon_client: AsyncClient) -> None:
        response = await anon_client.post(
            "/api/v1/agent/find-reservations", json={"phone": "912345678"}
        )

        assert response.status_code == 401


class TestCancelReservation:
    async def test_cancels_and_frees_the_table(
        self, agent_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        await create(agent_client)
        [r] = (await find(agent_client, phone="912345678"))["reservations"]

        assert await cancel(agent_client, r["id"], "912 345 678") == {"status": "cancelled"}

        assert await day_view(api_client, FRIDAY) == []
        assert await find(agent_client, phone="912345678") == {"reservations": []}
        # The same table can be booked again.
        assert await create(agent_client, phone="910000001") == {"status": "booked"}

    async def test_someone_elses_booking_is_not_found(
        self, agent_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        await create(agent_client)
        [r] = (await find(agent_client, phone="912345678"))["reservations"]

        assert await cancel(agent_client, r["id"], "910000009") == {"status": "not_found"}
        assert len(await day_view(api_client, FRIDAY)) == 1  # still booked

    @pytest.mark.parametrize(
        "reservation_id",
        ["00000000-0000-0000-0000-000000000000", "not-a-uuid", ""],
    )
    async def test_unknown_or_garbled_id_is_not_found(
        self, agent_client: AsyncClient, reservation_id: str
    ) -> None:
        assert await cancel(agent_client, reservation_id, "912345678") == {"status": "not_found"}

    async def test_cancelling_twice(self, agent_client: AsyncClient) -> None:
        await create(agent_client)
        [r] = (await find(agent_client, phone="912345678"))["reservations"]
        await cancel(agent_client, r["id"], "912345678")

        assert await cancel(agent_client, r["id"], "912345678") == {"status": "already_cancelled"}

    async def test_too_late_once_the_sitting_started(
        self, agent_client: AsyncClient, api_client: AsyncClient, clock: Clock
    ) -> None:
        await create(agent_client)
        [r] = (await find(agent_client, phone="912345678"))["reservations"]
        clock.now = datetime(2026, 10, 16, 20, 45, tzinfo=RESTAURANT_TZ)

        assert await cancel(agent_client, r["id"], "912345678") == {"status": "too_late"}
        assert len(await day_view(api_client, FRIDAY)) == 1

    async def test_requires_the_secret(self, anon_client: AsyncClient) -> None:
        response = await anon_client.post(
            "/api/v1/agent/cancel-reservation",
            json={"reservation_id": "00000000-0000-0000-0000-000000000000", "phone": "912345678"},
        )

        assert response.status_code == 401
