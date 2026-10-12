from datetime import datetime

from httpx import AsyncClient

from services.booking_rules import RESTAURANT_TZ
from tests.integration.conftest import Clock


async def availability(
    client: AsyncClient, *, date: str, party_size: int
) -> list[dict[str, object]]:
    response = await client.get(
        "/api/v1/availability", params={"date": date, "party_size": party_size}
    )
    assert response.status_code == 200, response.text
    body: list[dict[str, object]] = response.json()
    return body


async def test_open_day_has_every_slot_available(api_client: AsyncClient) -> None:
    slots = await availability(api_client, date="2026-10-16", party_size=4)

    assert [(s["start_time"], s["available"], s["reason"]) for s in slots] == [
        ("12:00:00", True, None),
        ("13:30:00", True, None),
        ("19:00:00", True, None),
        ("20:30:00", True, None),
    ]


async def test_monday_is_closed(api_client: AsyncClient) -> None:
    slots = await availability(api_client, date="2026-10-19", party_size=2)

    assert {(s["available"], s["reason"]) for s in slots} == {(False, "closed_day")}


async def test_uses_the_injected_clock(api_client: AsyncClient, clock: Clock) -> None:
    clock.now = datetime(2026, 10, 14, 12, 30, tzinfo=RESTAURANT_TZ)

    slots = await availability(api_client, date="2026-10-14", party_size=2)

    assert [s["reason"] for s in slots] == ["in_the_past", None, None, None]


async def test_party_too_large_is_explained_per_slot(api_client: AsyncClient) -> None:
    slots = await availability(api_client, date="2026-10-16", party_size=9)

    assert {s["reason"] for s in slots} == {"party_size_out_of_range"}


async def test_missing_or_malformed_params_use_the_standard_error_shape(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get(
        "/api/v1/availability", params={"date": "16/10/2026", "party_size": "four"}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert {e["field"] for e in body["details"]["errors"]} == {"date", "party_size"}
