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
