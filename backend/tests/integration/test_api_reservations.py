import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from tests.integration.conftest import Clock

# The test clock is Wednesday 14 Oct 2026, 10:00 Lisbon (see conftest).
FRIDAY, SATURDAY, MONDAY = "2026-10-16", "2026-10-17", "2026-10-19"


def payload(**overrides: Any) -> dict[str, Any]:
    return {
        "reservation_date": FRIDAY,
        "start_time": "20:30",
        "party_size": 2,
        "customer_name": "Ana Silva",
        "phone": "912 345 678",
        "notes": None,
    } | overrides


async def create(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/reservations", json=payload(**overrides))
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def list_reservations(client: AsyncClient, **params: str) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/reservations", params=params)
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] = response.json()
    return body


class TestCreate:
    async def test_returns_the_booking_with_customer_table_and_slot(
        self, api_client: AsyncClient
    ) -> None:
        r = await create(api_client, notes="Alergia: marisco")

        assert r["status"] == "confirmed"
        assert r["reservation_date"] == FRIDAY
        assert r["party_size"] == 2
        assert r["notes"] == "Alergia: marisco"
        assert r["customer"]["name"] == "Ana Silva"
        assert r["customer"]["phone"] == "+351912345678"
        assert r["table"]["name"] == "M1"
        assert r["booking_slot"]["start_time"] == "20:30:00"
        assert r["created_at"] and r["updated_at"]

    async def test_rule_violation_is_409_with_the_reason(self, api_client: AsyncClient) -> None:
        response = await api_client.post(
            "/api/v1/reservations", json=payload(reservation_date=MONDAY)
        )

        assert response.status_code == 409
        assert response.json()["code"] == "booking_rejected"
        assert response.json()["details"] == {"reason": "closed_day"}

    async def test_fully_booked_is_409(self, api_client: AsyncClient) -> None:
        await create(api_client, party_size=8, phone="910000001")

        response = await api_client.post(
            "/api/v1/reservations", json=payload(party_size=8, phone="910000002")
        )

        assert response.status_code == 409
        assert response.json()["details"] == {"reason": "fully_booked"}

    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"start_time": "21:00"}, "No sitting starts at 21:00."),
            ({"phone": "12345"}, "Invalid phone number."),
            ({"customer_name": "   "}, "Customer name is required."),
        ],
    )
    async def test_invalid_values_are_422(
        self, api_client: AsyncClient, overrides: dict[str, str], message: str
    ) -> None:
        response = await api_client.post("/api/v1/reservations", json=payload(**overrides))

        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"
        assert response.json()["message"] == message

    async def test_malformed_body_is_422_listing_the_fields(self, api_client: AsyncClient) -> None:
        body = payload(start_time="half past eight")
        del body["customer_name"]

        response = await api_client.post("/api/v1/reservations", json=body)

        assert response.status_code == 422
        fields = {e["field"] for e in response.json()["details"]["errors"]}
        assert fields == {"start_time", "customer_name"}


class TestGetAndCancel:
    async def test_get_by_id(self, api_client: AsyncClient) -> None:
        created = await create(api_client)

        response = await api_client.get(f"/api/v1/reservations/{created['id']}")

        assert response.status_code == 200
        assert response.json() == created

    async def test_unknown_id_is_404(self, api_client: AsyncClient) -> None:
        response = await api_client.get(f"/api/v1/reservations/{uuid.uuid4()}")

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    async def test_malformed_id_is_422(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/reservations/not-a-uuid")

        assert response.status_code == 422

    async def test_cancel_frees_the_table(self, api_client: AsyncClient) -> None:
        ana = await create(api_client, phone="910000001")

        response = await api_client.post(f"/api/v1/reservations/{ana['id']}/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        assert response.json()["updated_at"] >= ana["updated_at"]
        joao = await create(api_client, customer_name="João", phone="910000002")
        assert joao["table"]["name"] == ana["table"]["name"]

    async def test_cancel_twice_is_409(self, api_client: AsyncClient) -> None:
        r = await create(api_client)
        await api_client.post(f"/api/v1/reservations/{r['id']}/cancel")

        response = await api_client.post(f"/api/v1/reservations/{r['id']}/cancel")

        assert response.status_code == 409
        assert response.json()["code"] == "conflict"


class TestList:
    async def test_day_view_lists_confirmed_by_sitting_then_table(
        self, api_client: AsyncClient
    ) -> None:
        late_couple = await create(api_client, start_time="20:30", phone="910000001")
        late_four = await create(api_client, start_time="20:30", party_size=4, phone="910000002")
        early = await create(api_client, start_time="19:00", phone="910000003")
        cancelled = await create(api_client, start_time="12:00", phone="910000004")
        await api_client.post(f"/api/v1/reservations/{cancelled['id']}/cancel")
        await create(api_client, reservation_date=SATURDAY, phone="910000005")

        day = await list_reservations(api_client, date=FRIDAY)

        assert [r["id"] for r in day] == [early["id"], late_couple["id"], late_four["id"]]

    async def test_by_phone_returns_upcoming(self, api_client: AsyncClient) -> None:
        fri = await create(api_client)
        sat = await create(api_client, reservation_date=SATURDAY)
        await create(api_client, phone="910000009")

        found = await list_reservations(api_client, phone="+351 912 345 678")

        assert [r["id"] for r in found] == [fri["id"], sat["id"]]

    async def test_by_name_and_date(self, api_client: AsyncClient) -> None:
        ana = await create(api_client)
        await create(api_client, customer_name="Rui Costa", phone="910000009")

        found = await list_reservations(api_client, name="silva", date=FRIDAY)

        assert [r["id"] for r in found] == [ana["id"]]

    async def test_by_name_alone_spans_dates_soonest_first(
        self, api_client: AsyncClient, clock: Clock
    ) -> None:
        sat = await create(api_client, reservation_date=SATURDAY, phone="910000001")
        fri_dinner = await create(api_client, start_time="20:30", phone="910000002")
        fri_lunch = await create(api_client, start_time="12:00", phone="910000003")
        cancelled = await create(api_client, start_time="19:00", phone="910000004")
        await api_client.post(f"/api/v1/reservations/{cancelled['id']}/cancel")
        await create(api_client, customer_name="Rui Costa", phone="910000009")
        today_lunch = await create(api_client, reservation_date="2026-10-14", start_time="12:00")

        found = await list_reservations(api_client, name="SILVA")

        assert [r["id"] for r in found] == [
            today_lunch["id"],
            fri_lunch["id"],
            fri_dinner["id"],
            sat["id"],
        ]

        # Sittings that already started drop out.
        clock.now = clock.now.replace(hour=13)
        later = await list_reservations(api_client, name="silva")
        assert today_lunch["id"] not in [r["id"] for r in later]

    async def test_blank_name_is_422(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/reservations", params={"name": "  "})

        assert response.status_code == 422
        assert response.json()["message"] == "Name is required."

    @pytest.mark.parametrize(
        "params",
        [
            {},
            {"phone": "912345678", "name": "ana"},
            {"phone": "912345678", "date": FRIDAY},
            {"phone": "912345678", "name": "ana", "date": FRIDAY},
        ],
    )
    async def test_unsupported_filter_combinations_are_422(
        self, api_client: AsyncClient, params: dict[str, str]
    ) -> None:
        response = await api_client.get("/api/v1/reservations", params=params)

        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"
