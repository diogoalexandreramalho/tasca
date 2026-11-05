"""Building, signing and sending ElevenLabs post-call webhooks in tests."""

import json
import time
from datetime import UTC, datetime
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.webhooks import sign_elevenlabs
from models import Call
from tests.conftest import TEST_WEBHOOK_SECRET

URL = "/api/v1/webhooks/elevenlabs/post-call"
STARTED = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)


def payload(
    conversation_id: str = "conv_1",
    *,
    tools: tuple[str, ...] = (),
    started: datetime = STARTED,
    summary: str | None = "Caller asked for a table.",
) -> dict[str, Any]:
    transcript: list[dict[str, Any]] = [
        {"role": "agent", "message": "Hello, how can I help?", "time_in_call_secs": 0},
        {"role": "user", "message": "A table for two on Friday.", "time_in_call_secs": 3.4},
    ]
    for name in tools:
        transcript.append(
            {
                "role": "agent",
                "message": None,
                "time_in_call_secs": 5,
                "tool_calls": [{"tool_name": name, "params_as_json": "{}"}],
                "tool_results": [{"result_value": "{}"}],
                "conversation_turn_metrics": {"anything": 1},
            }
        )
    return {
        "type": "post_call_transcription",
        "event_timestamp": int(started.timestamp()) + 120,
        "data": {
            "agent_id": "agent_x",
            "conversation_id": conversation_id,
            "status": "done",
            "transcript": transcript,
            "metadata": {
                "start_time_unix_secs": int(started.timestamp()),
                "call_duration_secs": 95,
                "cost": 12,
            },
            "analysis": {"transcript_summary": summary, "call_successful": "success"},
        },
    }


async def send(
    client: AsyncClient,
    body: dict[str, Any],
    *,
    secret: str = TEST_WEBHOOK_SECRET,
    timestamp: int | None = None,
    signature: str | None = None,
) -> Response:
    raw = json.dumps(body).encode()
    header = signature or sign_elevenlabs(raw, secret, timestamp or int(time.time()))
    return await client.post(
        URL,
        content=raw,
        headers={"ElevenLabs-Signature": header, "Content-Type": "application/json"},
    )


async def calls(factory: async_sessionmaker[AsyncSession]) -> list[Call]:
    async with factory() as s:
        return list((await s.execute(select(Call).order_by(Call.started_at))).scalars())


async def agent_book(agent_client: AsyncClient, conversation_id: str) -> str:
    response = await agent_client.post(
        "/api/v1/agent/create-reservation",
        json={
            "date": "2026-10-16",
            "time": "20:30",
            "party_size": 2,
            "name": "Ana",
            "phone": "912345678",
            "conversation_id": conversation_id,
        },
    )
    assert response.json() == {"status": "booked"}
    found = await agent_client.post("/api/v1/agent/find-reservations", json={"phone": "912345678"})
    reservation_id: str = found.json()["reservations"][0]["id"]
    return reservation_id
