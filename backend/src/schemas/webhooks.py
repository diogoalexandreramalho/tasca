"""The parts of ElevenLabs' post-call webhook we use.

Only the fields we need are declared; everything else ElevenLabs sends (costs,
audio flags, evaluation criteria, ...) is ignored, so new fields on their side
never break us.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ToolCall(_Lenient):
    tool_name: str | None = None


class TranscriptTurn(_Lenient):
    role: str
    message: str | None = None
    time_in_call_secs: float = 0
    tool_calls: list[ToolCall] | None = None


class CallMetadata(_Lenient):
    start_time_unix_secs: int
    call_duration_secs: int


class CallAnalysis(_Lenient):
    transcript_summary: str | None = None


class PostCallTranscription(_Lenient):
    conversation_id: str
    transcript: list[TranscriptTurn] = []
    metadata: CallMetadata
    analysis: CallAnalysis | None = None


class WebhookEnvelope(_Lenient):
    type: str
    data: dict[str, Any]


class WebhookAck(BaseModel):
    status: str  # "recorded" or "ignored"
