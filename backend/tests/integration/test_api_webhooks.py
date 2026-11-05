"""ElevenLabs' post-call webhook, signed and sent like ElevenLabs does."""

import json
import time
from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.config import get_settings
from core.webhooks import sign_elevenlabs
from models import CallOutcome
from tests.conftest import TEST_WEBHOOK_SECRET
from tests.integration.conftest import Clock
from tests.integration.webhook_helpers import STARTED, URL, agent_book, calls, payload, send


class TestSignature:
    async def test_valid_signature_is_recorded(
        self, anon_client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        response = await send(anon_client, payload())

        assert response.status_code == 200
        assert response.json() == {"status": "recorded"}
        assert len(await calls(session_factory)) == 1

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"secret": "someone-else"}, "Invalid webhook signature."),
            ({"timestamp": int(time.time()) - 31 * 60}, "Webhook signature expired."),
            ({"signature": "t=1,v0=nope"}, "Webhook signature expired."),
        ],
    )
    async def test_bad_signatures_are_rejected_and_nothing_is_saved(
        self,
        anon_client: AsyncClient,
        session_factory: async_sessionmaker[AsyncSession],
        kwargs: dict[str, Any],
        message: str,
    ) -> None:
        response = await send(anon_client, payload(), **kwargs)

        assert response.status_code == 401
        assert response.json()["message"] == message
        assert await calls(session_factory) == []

    async def test_missing_signature(self, anon_client: AsyncClient) -> None:
        response = await anon_client.post(URL, json=payload())

        assert response.status_code == 401
        assert response.json()["message"] == "Missing webhook signature."

    async def test_tampered_body(self, anon_client: AsyncClient) -> None:
        raw = json.dumps(payload()).encode()
        header = sign_elevenlabs(raw, TEST_WEBHOOK_SECRET, int(time.time()))

        response = await anon_client.post(
            URL, content=raw.replace(b"conv_1", b"conv_2"), headers={"ElevenLabs-Signature": header}
        )

        assert response.status_code == 401

    async def test_unconfigured_secret_rejects_everything(
        self, anon_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(get_settings(), "elevenlabs_webhook_secret", None)

        response = await send(anon_client, payload())

        assert response.status_code == 401


class TestRecording:
    async def test_stores_only_the_essentials(
        self, anon_client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        await send(anon_client, payload(tools=("check_availability",)))

        [call] = await calls(session_factory)
        assert call.conversation_id == "conv_1"
        assert call.started_at == STARTED
        assert call.duration_secs == 95
        assert call.summary == "Caller asked for a table."
        # Turns without text (tool calls) are dropped; no tool payloads or metrics.
        assert call.transcript == [
            {"role": "agent", "message": "Hello, how can I help?", "time_in_call_secs": 0},
            {"role": "user", "message": "A table for two on Friday.", "time_in_call_secs": 3},
        ]

    async def test_a_redelivery_updates_the_same_call(
        self, anon_client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        await send(anon_client, payload(summary="First."))
        await send(anon_client, payload(summary="Second."))

        [call] = await calls(session_factory)
        assert call.summary == "Second."

    async def test_other_event_types_are_acknowledged_and_ignored(
        self, anon_client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        response = await send(
            anon_client,
            {"type": "post_call_audio", "data": {"conversation_id": "conv_1", "full_audio": "..."}},
        )

        assert response.json() == {"status": "ignored"}
        assert await calls(session_factory) == []

    async def test_signed_but_unrecognised_payload_is_a_422(self, anon_client: AsyncClient) -> None:
        response = await send(
            anon_client, {"type": "post_call_transcription", "data": {"conversation_id": "x"}}
        )

        assert response.status_code == 422


class TestOutcome:
    async def test_booked(
        self,
        anon_client: AsyncClient,
        agent_client: AsyncClient,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await agent_book(agent_client, "conv_book")

        await send(
            anon_client, payload("conv_book", tools=("check_availability", "create_reservation"))
        )

        [call] = await calls(session_factory)
        assert call.outcome is CallOutcome.BOOKED

    async def test_cancelled(
        self,
        anon_client: AsyncClient,
        agent_client: AsyncClient,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        reservation_id = await agent_book(agent_client, "conv_earlier")
        await agent_client.post(
            "/api/v1/agent/cancel-reservation",
            json={
                "reservation_id": reservation_id,
                "phone": "912345678",
                "conversation_id": "conv_cancel",
            },
        )

        await send(
            anon_client, payload("conv_cancel", tools=("find_reservations", "cancel_reservation"))
        )

        [call] = await calls(session_factory)
        assert call.outcome is CallOutcome.CANCELLED

    async def test_enquiry_when_tools_were_used_but_nothing_changed(
        self, anon_client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        await send(anon_client, payload(tools=("check_availability",)))

        [call] = await calls(session_factory)
        assert call.outcome is CallOutcome.ENQUIRY

    async def test_no_action_when_only_system_tools_or_none(
        self, anon_client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        await send(anon_client, payload("conv_a", tools=("end_call",)))
        await send(anon_client, payload("conv_b"))

        assert [c.outcome for c in await calls(session_factory)] == [
            CallOutcome.NO_ACTION,
            CallOutcome.NO_ACTION,
        ]


class TestRetention:
    async def test_old_transcripts_are_cleared_when_a_new_call_arrives(
        self,
        anon_client: AsyncClient,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Clock,
    ) -> None:
        # The test clock is 14 Oct 2026; 91 days earlier is past the 90-day limit.
        old_start = clock.now - timedelta(days=91)
        await send(
            anon_client, payload("conv_old", started=old_start, tools=("check_availability",))
        )
        await send(anon_client, payload("conv_new"))

        old, new = await calls(session_factory)
        assert old.conversation_id == "conv_old"
        assert old.summary is None
        assert old.transcript is None
        # Kept for statistics.
        assert old.duration_secs == 95
        assert old.outcome is CallOutcome.ENQUIRY
        assert new.summary is not None
        assert new.transcript
