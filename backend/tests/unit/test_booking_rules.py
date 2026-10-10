from datetime import UTC, date, datetime, time, timedelta

import pytest

from models import DiningTable
from services.booking_rules import (
    RESTAURANT_TZ,
    Rejection,
    check_booking,
    pick_table,
    slot_start,
)

# Wednesday 14 Oct 2026, 10:00 in Lisbon.
NOW = datetime(2026, 10, 14, 10, 0, tzinfo=RESTAURANT_TZ)
DINNER = time(20, 30)


def check(
    reservation_date: date = date(2026, 10, 16),  # Friday
    start_time: time = DINNER,
    party_size: int = 2,
    now: datetime = NOW,
) -> Rejection | None:
    return check_booking(
        reservation_date=reservation_date, start_time=start_time, party_size=party_size, now=now
    )


class TestCheckBooking:
    def test_valid_request_is_allowed(self) -> None:
        assert check() is None

    @pytest.mark.parametrize("party_size", [1, 8])
    def test_party_size_limits_are_inclusive(self, party_size: int) -> None:
        assert check(party_size=party_size) is None

    @pytest.mark.parametrize("party_size", [0, 9, 20])
    def test_party_size_out_of_range(self, party_size: int) -> None:
        assert check(party_size=party_size) is Rejection.PARTY_SIZE_OUT_OF_RANGE

    def test_monday_is_closed(self) -> None:
        assert check(reservation_date=date(2026, 10, 19)) is Rejection.CLOSED_DAY

    def test_sunday_is_open(self) -> None:
        assert check(reservation_date=date(2026, 10, 18)) is None

    def test_earlier_today_is_in_the_past(self) -> None:
        assert check(reservation_date=NOW.date(), start_time=time(9, 0)) is Rejection.IN_THE_PAST

    def test_slot_starting_right_now_is_in_the_past(self) -> None:
        assert check(reservation_date=NOW.date(), start_time=time(10, 0)) is Rejection.IN_THE_PAST

    def test_yesterday_is_in_the_past(self) -> None:
        assert check(reservation_date=date(2026, 10, 13)) is Rejection.IN_THE_PAST

    def test_less_than_one_hour_ahead_is_too_soon(self) -> None:
        now = datetime(2026, 10, 14, 19, 31, tzinfo=RESTAURANT_TZ)
        assert check(reservation_date=now.date(), now=now) is Rejection.TOO_SOON

    def test_exactly_one_hour_ahead_is_allowed(self) -> None:
        now = datetime(2026, 10, 14, 19, 30, tzinfo=RESTAURANT_TZ)
        assert check(reservation_date=now.date(), now=now) is None

    def test_sixty_days_ahead_is_allowed(self) -> None:
        assert check(reservation_date=NOW.date() + timedelta(days=60)) is None  # Sunday

    def test_more_than_sixty_days_ahead_is_too_far(self) -> None:
        assert check(reservation_date=date(2026, 12, 15)) is Rejection.TOO_FAR_AHEAD  # Tuesday

    def test_now_in_utc_is_compared_in_lisbon_time(self) -> None:
        # 18:45 UTC is 19:45 in Lisbon (summer time), so 20:30 is only 45 min away.
        now = datetime(2026, 10, 14, 18, 45, tzinfo=UTC)
        assert check(reservation_date=date(2026, 10, 14), now=now) is Rejection.TOO_SOON

    def test_naive_now_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            check(now=datetime(2026, 10, 14, 10, 0))


class TestSlotStart:
    def test_uses_lisbon_offset_across_daylight_saving_change(self) -> None:
        # Clocks go back on Sunday 25 Oct 2026: +01:00 before, +00:00 after.
        assert slot_start(date(2026, 10, 24), DINNER).utcoffset() == timedelta(hours=1)
        assert slot_start(date(2026, 10, 25), DINNER).utcoffset() == timedelta(0)


def table(id: int, min_capacity: int, max_capacity: int, is_active: bool = True) -> DiningTable:
    return DiningTable(
        id=id,
        name=f"M{id}",
        min_capacity=min_capacity,
        max_capacity=max_capacity,
        is_active=is_active,
    )


# Same shape as the seed: 2-seaters, 4-seaters, 6-seaters and one 8-seater.
# Bigger tables get lower ids so "smallest" and "lowest id" never agree by accident.
EIGHT = table(1, 5, 8)
SIX = table(2, 3, 6)
FOUR_A, FOUR_B = table(3, 2, 4), table(4, 2, 4)
TWO_A, TWO_B = table(5, 1, 2), table(6, 1, 2)
TWO_SEATERS = {TWO_A.id, TWO_B.id}
ROOM = [SIX, TWO_B, EIGHT, FOUR_B, TWO_A, FOUR_A]  # deliberately unsorted


class TestPickTable:
    def test_picks_smallest_table_that_fits(self) -> None:
        assert pick_table(ROOM, party_size=2, taken_table_ids=set()) is TWO_A

    def test_ties_go_to_lowest_id(self) -> None:
        assert pick_table(ROOM, party_size=3, taken_table_ids=set()) is FOUR_A

    def test_skips_taken_tables(self) -> None:
        assert pick_table(ROOM, party_size=2, taken_table_ids=TWO_SEATERS) is FOUR_A

    def test_couple_cannot_take_the_eight_seater(self) -> None:
        taken = {t.id for t in ROOM if t is not EIGHT}
        assert pick_table(ROOM, party_size=2, taken_table_ids=taken) is None

    def test_party_of_five_gets_the_eight_seater_when_six_seater_is_taken(self) -> None:
        assert pick_table(ROOM, party_size=5, taken_table_ids={SIX.id}) is EIGHT

    def test_respects_minimum_capacity(self) -> None:
        # A single diner can't take a 4-seater (min 2) even when every 2-seater is taken.
        assert pick_table(ROOM, party_size=1, taken_table_ids=TWO_SEATERS) is None

    def test_ignores_inactive_tables(self) -> None:
        inactive_two = table(7, 1, 2, is_active=False)
        assert pick_table([inactive_two, FOUR_A], party_size=2, taken_table_ids=set()) is FOUR_A

    def test_returns_none_when_room_is_full(self) -> None:
        all_ids = {t.id for t in ROOM}
        assert pick_table(ROOM, party_size=4, taken_table_ids=all_ids) is None
