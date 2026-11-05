import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel

from models import CallOutcome, ReservationStatus


class CallBooking(BaseModel):
    """A reservation this call created or cancelled. Enough to show and link it."""

    id: uuid.UUID
    action: Literal["created", "cancelled"]
    reservation_date: date
    start_time: time
    party_size: int
    customer_name: str
    status: ReservationStatus  # current status (a booking made by phone may be cancelled later)


class CallRead(BaseModel):
    id: uuid.UUID
    started_at: datetime
    duration_secs: int
    outcome: CallOutcome
    summary: str | None  # None once cleared by retention
    bookings: list[CallBooking]


class TranscriptLine(BaseModel):
    role: str  # "agent" or "user"
    message: str
    time_in_call_secs: int


class CallDetail(CallRead):
    transcript: list[TranscriptLine] | None  # None once cleared by retention
