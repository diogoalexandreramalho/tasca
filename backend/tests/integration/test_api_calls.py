"""The dashboard's call log API (admin only)."""

from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient

from tests.integration.webhook_helpers import agent_book, payload, send

# Lisbon is UTC+1 in October: 23:30 UTC on the 13th is 00:30 on the 14th in Lisbon.
JUST_AFTER_MIDNIGHT_14TH = datetime(2026, 10, 13, 23, 30, tzinfo=UTC)
MORNING_14TH = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
EVENING_14TH = datetime(2026, 10, 14, 18, 0, tzinfo=UTC)
LATE_13TH = datetime(2026, 10, 13, 22, 30, tzinfo=UTC)  # 23:30 on the 13th in Lisbon


async def list_calls(client: AsyncClient, **params: str) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/calls", params=params)
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] = response.json()
    return body


class TestListCalls:
    async def test_a_days_calls_in_lisbon_time_newest_first(
        self, anon_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        for conversation_id, started in [
            ("conv_morning", MORNING_14TH),
            ("conv_evening", EVENING_14TH),
            ("conv_just_after_midnight", JUST_AFTER_MIDNIGHT_14TH),
            ("conv_previous_day", LATE_13TH),
        ]:
            await send(anon_client, payload(conversation_id, started=started))

        day = await list_calls(api_client, date="2026-10-14")

        assert [c["started_at"] for c in day] == [
            "2026-10-14T18:00:00Z",
            "2026-10-14T09:00:00Z",
            "2026-10-13T23:30:00Z",  # 00:30 in Lisbon, so it belongs to the 14th
        ]

    async def test_without_a_date_lists_the_most_recent(
        self, anon_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        await send(anon_client, payload("conv_a", started=MORNING_14TH))
        await send(anon_client, payload("conv_b", started=LATE_13TH))

        assert len(await list_calls(api_client)) == 2

    async def test_list_items_have_no_transcript(
        self, anon_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        await send(anon_client, payload(started=MORNING_14TH))

        [call] = await list_calls(api_client, date="2026-10-14")

        assert set(call) == {
            "id",
            "started_at",
            "duration_secs",
            "outcome",
            "summary",
            "bookings",
        }
        assert call["outcome"] == "no_action"
        assert call["summary"] == "Caller asked for a table."

    async def test_shows_the_bookings_a_call_created_and_cancelled(
        self, anon_client: AsyncClient, agent_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        # One conversation books; a later one cancels that booking.
        reservation_id = await agent_book(agent_client, "conv_book")
        await agent_client.post(
            "/api/v1/agent/cancel-reservation",
            json={
                "reservation_id": reservation_id,
                "phone": "912345678",
                "conversation_id": "conv_cancel",
            },
        )
        await send(anon_client, payload("conv_book", started=MORNING_14TH))
        await send(anon_client, payload("conv_cancel", started=EVENING_14TH))

        cancel_call, book_call = await list_calls(api_client, date="2026-10-14")

        expected = {
            "id": reservation_id,
            "reservation_date": "2026-10-16",
            "start_time": "20:30:00",
            "party_size": 2,
            "customer_name": "Ana",
            "status": "cancelled",  # its status now, not at booking time
        }
        assert book_call["outcome"] == "booked"
        assert book_call["bookings"] == [{**expected, "action": "created"}]
        assert cancel_call["outcome"] == "cancelled"
        assert cancel_call["bookings"] == [{**expected, "action": "cancelled"}]


class TestCallDetail:
    async def test_includes_the_transcript(
        self, anon_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        await send(anon_client, payload(started=MORNING_14TH))
        [listed] = await list_calls(api_client, date="2026-10-14")

        response = await api_client.get(f"/api/v1/calls/{listed['id']}")

        assert response.status_code == 200
        detail = response.json()
        assert {k: v for k, v in detail.items() if k != "transcript"} == listed
        assert detail["transcript"] == [
            {"role": "agent", "message": "Hello, how can I help?", "time_in_call_secs": 0},
            {"role": "user", "message": "A table for two on Friday.", "time_in_call_secs": 3},
        ]

    async def test_transcript_is_null_once_cleared_by_retention(
        self, anon_client: AsyncClient, api_client: AsyncClient
    ) -> None:
        old = MORNING_14TH - timedelta(days=100)
        await send(anon_client, payload("conv_old", started=old))
        await send(anon_client, payload("conv_new", started=MORNING_14TH))
        [listed] = await list_calls(api_client, date=old.date().isoformat())

        detail = (await api_client.get(f"/api/v1/calls/{listed['id']}")).json()

        assert detail["summary"] is None
        assert detail["transcript"] is None

    async def test_unknown_call_is_404(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/calls/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404


class TestAuth:
    async def test_requires_the_admin_login(self, anon_client: AsyncClient) -> None:
        assert (await anon_client.get("/api/v1/calls")).status_code == 401

    async def test_the_agent_secret_is_not_enough(self, agent_client: AsyncClient) -> None:
        # Transcripts are for staff only.
        assert (await agent_client.get("/api/v1/calls")).status_code == 401
