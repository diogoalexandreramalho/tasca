"""Request/response shapes for the voice agent's tools.

Replies carry only the facts the model needs for its next step; the wording is
the model's job (guided by the agent's prompt). No other customers' data, no
table numbers, no echo of what the model just sent.

Read tools (check, find) signal "nothing" with an empty list. Write tools
(create, cancel) return a `status` word, because they have several distinct
outcomes the model must tell apart.

Business outcomes ("closed", "fully booked", "not found") are normal HTTP 200
replies: they're things the agent should say. Only a missing/wrong secret (401)
or malformed input (422) are HTTP errors, and those mean a misconfigured tool.

Field descriptions end up in the API docs; mirror them in the ElevenLabs tool
definitions, since that's the only thing the model reads about a tool.
"""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from services.booking_rules import Rejection


class CheckAvailabilityRequest(BaseModel):
    date: dt.date = Field(description="Day of the booking, YYYY-MM-DD.")
    party_size: int = Field(description="Number of people, including the caller.")


class CheckAvailabilityReply(BaseModel):
    available_times: list[str] = Field(
        description='Start times with a free table, "HH:MM". Pass one to create_reservation.'
    )
    reason: Rejection | None = Field(
        default=None, description="Why nothing is available. Only present when the list is empty."
    )


class CreateReservationRequest(BaseModel):
    date: dt.date = Field(description="Day of the booking, YYYY-MM-DD.")
    # A string, not dt.time: a time the model got wrong ("8:30 PM", "21:00") should
    # come back as status "invalid" the agent can act on, not as a 422.
    time: str = Field(description='Start of the sitting, "HH:MM", one of available_times.')
    party_size: int = Field(description="Number of people, including the caller.")
    name: str = Field(description="Name the booking is under.")
    phone: str = Field(description="Caller's phone number, any format.")
    notes: str | None = Field(
        default=None,
        description='Optional. Allergies must start with "Alergia:", e.g. "Alergia: marisco".',
    )


class CreateReservationReply(BaseModel):
    status: Literal["booked", "already_booked", "rejected", "invalid"] = Field(
        description=(
            "booked: done. already_booked: this phone already has a booking at that date "
            "and time, nothing new was created. rejected: see `reason`. invalid: see `field`."
        )
    )
    reason: Rejection | None = Field(default=None, description="Why it was rejected.")
    available_times: list[str] | None = Field(
        default=None, description='Other free times that day, "HH:MM". Only when fully booked.'
    )
    field: Literal["name", "phone", "time"] | None = Field(
        default=None, description="Which input to ask the caller for again."
    )


class FindReservationsRequest(BaseModel):
    phone: str = Field(description="Phone number the booking was made with, any format.")
    date: dt.date | None = Field(
        default=None, description="Optional. Only bookings on this day, YYYY-MM-DD."
    )


class AgentReservation(BaseModel):
    """Just enough to confirm a booking with the caller and cancel it. No table,
    no notes, no phone: the caller already knows their own number."""

    id: str = Field(description="Pass to cancel_reservation. Never read it aloud.")
    date: dt.date
    time: str = Field(description='"HH:MM"')
    party_size: int
    name: str


class FindReservationsReply(BaseModel):
    reservations: list[AgentReservation] = Field(
        description="Upcoming confirmed bookings for this phone, soonest first."
    )
    field: Literal["phone"] | None = Field(
        default=None, description="Present when the phone number is invalid: ask for it again."
    )


class CancelReservationRequest(BaseModel):
    # A string, not a UUID: a garbled id from the model is just "not_found".
    reservation_id: str = Field(description="The `id` from find_reservations.")
    phone: str = Field(description="Phone number the booking was made with.")


class CancelReservationReply(BaseModel):
    status: Literal["cancelled", "not_found", "already_cancelled", "too_late"] = Field(
        description=(
            "cancelled: done. not_found: no such booking for this phone. "
            "already_cancelled: nothing to do. too_late: the sitting has already started."
        )
    )
