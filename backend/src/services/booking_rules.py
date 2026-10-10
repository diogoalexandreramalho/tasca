"""Booking rules for Tasca Tagarela, as pure functions (no DB, no clock).

The service layer loads tables and existing reservations, passes `now` in, and
turns a `Rejection` into an error the agent can explain to the caller.
"""

import enum
from collections.abc import Collection, Sequence
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from models import DiningTable

RESTAURANT_TZ = ZoneInfo("Europe/Lisbon")

# Monday=0 ... Sunday=6. Closed on Mondays.
OPEN_WEEKDAYS = frozenset({1, 2, 3, 4, 5, 6})
MIN_PARTY_SIZE = 1
MAX_PARTY_SIZE = 8  # larger groups are handed off to a human
MIN_NOTICE = timedelta(hours=1)
MAX_DAYS_AHEAD = 60


class Rejection(enum.StrEnum):
    PARTY_SIZE_OUT_OF_RANGE = "party_size_out_of_range"
    CLOSED_DAY = "closed_day"
    IN_THE_PAST = "in_the_past"
    TOO_SOON = "too_soon"
    TOO_FAR_AHEAD = "too_far_ahead"
    # Set by the reservation service when no suitable table is free, never by `check_booking`.
    FULLY_BOOKED = "fully_booked"


def slot_start(reservation_date: date, start_time: time) -> datetime:
    """When a sitting starts, as an aware datetime in the restaurant's timezone."""
    return datetime.combine(reservation_date, start_time, tzinfo=RESTAURANT_TZ)


def check_booking(
    *,
    reservation_date: date,
    start_time: time,
    party_size: int,
    now: datetime,
) -> Rejection | None:
    """Return why a booking request breaks the rules, or None if it's allowed.

    Doesn't check table availability — see `pick_table`.
    """
    if now.tzinfo is None:
        raise ValueError("`now` must be timezone-aware")

    if not MIN_PARTY_SIZE <= party_size <= MAX_PARTY_SIZE:
        return Rejection.PARTY_SIZE_OUT_OF_RANGE

    if reservation_date.weekday() not in OPEN_WEEKDAYS:
        return Rejection.CLOSED_DAY

    starts_at = slot_start(reservation_date, start_time)
    if starts_at <= now:
        return Rejection.IN_THE_PAST
    if starts_at - now < MIN_NOTICE:
        return Rejection.TOO_SOON

    today = now.astimezone(RESTAURANT_TZ).date()
    if reservation_date > today + timedelta(days=MAX_DAYS_AHEAD):
        return Rejection.TOO_FAR_AHEAD

    return None


def table_fits(table: DiningTable, party_size: int) -> bool:
    return table.is_active and table.min_capacity <= party_size <= table.max_capacity


def pick_table(
    tables: Sequence[DiningTable],
    party_size: int,
    taken_table_ids: Collection[int],
) -> DiningTable | None:
    """Smallest free table that fits the party, or None.

    "Smallest" keeps bigger tables free for bigger groups. Ties go to the lowest id.
    """
    candidates = [t for t in tables if t.id not in taken_table_ids and table_fits(t, party_size)]
    return min(candidates, key=lambda t: (t.max_capacity, t.id), default=None)
