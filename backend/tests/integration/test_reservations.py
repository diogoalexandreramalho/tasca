import asyncio
import uuid
from datetime import date, datetime, time
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.exceptions import (
    BookingRejectedError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from models import Customer, Reservation, ReservationStatus
from repositories import reservation as reservation_repo
from services import reservations
from services.booking_rules import RESTAURANT_TZ, Rejection

# Wednesday 14 Oct 2026, 10:00 in Lisbon.
NOW = datetime(2026, 10, 14, 10, 0, tzinfo=RESTAURANT_TZ)
FRIDAY = date(2026, 10, 16)
SATURDAY = date(2026, 10, 17)
MONDAY = date(2026, 10, 19)
LUNCH_1, LUNCH_2, DINNER_1, DINNER_2 = time(12, 0), time(13, 30), time(19, 0), time(20, 30)


async def book(
    session: AsyncSession,
    *,
    phone: str = "912 345 678",
    name: str = "Ana Silva",
    party_size: int = 2,
    reservation_date: date = FRIDAY,
    start_time: time = DINNER_2,
    notes: str | None = None,
    now: datetime = NOW,
) -> Reservation:
    return await reservations.create_reservation(
        session,
        reservation_date=reservation_date,
        start_time=start_time,
        party_size=party_size,
        customer_name=name,
        phone=phone,
        notes=notes,
        now=now,
    )


def phone_number(n: int) -> str:
    return f"91{n:07d}"


async def count(session: AsyncSession, model: type[Customer] | type[Reservation]) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


class TestCreateReservation:
    async def test_assigns_smallest_table_and_normalizes_phone(self, session: AsyncSession) -> None:
        r = await book(session, notes="  Alergia: marisco  ")

        assert r.table.name == "M1"
        assert r.status is ReservationStatus.CONFIRMED
        assert r.customer.phone == "+351912345678"
        assert r.customer.name == "Ana Silva"
        assert r.booking_slot.start_time == DINNER_2
        assert r.notes == "Alergia: marisco"

    async def test_next_couple_gets_next_two_seater(self, session: AsyncSession) -> None:
        await book(session, phone=phone_number(1))
        r = await book(session, phone=phone_number(2))
        assert r.table.name == "M2"

    async def test_rule_violation_is_rejected_and_nothing_is_saved(
        self, session: AsyncSession
    ) -> None:
        with pytest.raises(BookingRejectedError) as exc:
            await book(session, reservation_date=MONDAY)

        assert exc.value.reason == Rejection.CLOSED_DAY
        assert await count(session, Reservation) == 0
        assert await count(session, Customer) == 0

    async def test_unknown_start_time_is_invalid(self, session: AsyncSession) -> None:
        with pytest.raises(ValidationAppError, match="No sitting starts at 21:00"):
            await book(session, start_time=time(21, 0))

    async def test_invalid_phone_is_rejected(self, session: AsyncSession) -> None:
        with pytest.raises(ValidationAppError, match="Invalid phone"):
            await book(session, phone="12345")

    async def test_fully_booked_when_no_fitting_table_is_left(self, session: AsyncSession) -> None:
        # Couples fit the six 2-seaters and the six 4-seaters (min 2), not the 6/8-seaters.
        for n in range(12):
            await book(session, phone=phone_number(n))

        with pytest.raises(BookingRejectedError) as exc:
            await book(session, phone=phone_number(99))

        assert exc.value.reason == Rejection.FULLY_BOOKED
        assert await count(session, Reservation) == 12

    async def test_same_phone_reuses_customer_and_updates_name(self, session: AsyncSession) -> None:
        await book(session, name="Ana")
        await book(session, name="Ana Silva", reservation_date=SATURDAY)

        assert await count(session, Customer) == 1
        customer = (await session.execute(select(Customer))).scalar_one()
        assert customer.name == "Ana Silva"


@pytest.fixture
def force_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make two concurrent bookings both read the free tables before either inserts.

    Without this, the second call is usually still opening its DB connection when
    the first one commits, so the race (and the retry path) never happens.
    """
    barrier = asyncio.Barrier(2)
    read_taken = reservation_repo.taken_table_ids

    async def taken_then_wait(*args: Any, **kwargs: Any) -> set[int]:
        taken = await read_taken(*args, **kwargs)
        await barrier.wait()
        return taken

    monkeypatch.setattr(reservation_repo, "taken_table_ids", taken_then_wait)


@pytest.mark.usefixtures("force_collision")
class TestConcurrentBookings:
    async def test_two_calls_for_the_last_table_book_it_once(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        # Only the 8-seater fits a party of 8.
        async def attempt(phone: str) -> Reservation | BookingRejectedError:
            async with session_factory() as s:
                try:
                    return await book(s, phone=phone, party_size=8)
                except BookingRejectedError as exc:
                    return exc

        results = await asyncio.gather(attempt(phone_number(1)), attempt(phone_number(2)))

        booked = [r for r in results if isinstance(r, Reservation)]
        rejected = [r for r in results if isinstance(r, BookingRejectedError)]
        assert len(booked) == 1
        assert booked[0].table.name == "M15"
        assert len(rejected) == 1
        assert rejected[0].reason == Rejection.FULLY_BOOKED

    async def test_two_calls_for_the_same_table_both_get_one(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        # A party of 5 fits M13, M14 (3-6) and M15 (5-8); both calls start by picking M13.
        async def attempt(phone: str) -> Reservation:
            async with session_factory() as s:
                return await book(s, phone=phone, party_size=5)

        results = await asyncio.gather(attempt(phone_number(1)), attempt(phone_number(2)))

        assert sorted(r.table.name for r in results) == ["M13", "M14"]


class TestCancelReservation:
    async def test_cancel_frees_the_table_and_keeps_history(self, session: AsyncSession) -> None:
        ana = await book(session, name="Ana", phone=phone_number(1))
        await reservations.cancel_reservation(session, reservation_id=ana.id, now=NOW)
        joao = await book(session, name="João", phone=phone_number(2))

        assert joao.table.name == ana.table.name == "M1"
        statuses = (
            await session.execute(select(Reservation.status).order_by(Reservation.created_at))
        ).scalars()
        assert list(statuses) == [ReservationStatus.CANCELLED, ReservationStatus.CONFIRMED]

    async def test_cancelling_twice_is_a_conflict(self, session: AsyncSession) -> None:
        r = await book(session)
        await reservations.cancel_reservation(session, reservation_id=r.id, now=NOW)

        with pytest.raises(ConflictError, match="already cancelled"):
            await reservations.cancel_reservation(session, reservation_id=r.id, now=NOW)

    async def test_cannot_cancel_once_the_sitting_has_started(self, session: AsyncSession) -> None:
        r = await book(session)
        started = datetime(2026, 10, 16, 20, 45, tzinfo=RESTAURANT_TZ)

        with pytest.raises(ConflictError, match="already started"):
            await reservations.cancel_reservation(session, reservation_id=r.id, now=started)

    async def test_unknown_reservation_is_not_found(self, session: AsyncSession) -> None:
        with pytest.raises(NotFoundError):
            await reservations.cancel_reservation(session, reservation_id=uuid.uuid4(), now=NOW)


class TestFindReservations:
    async def test_by_phone_in_any_format_returns_upcoming_in_order(
        self, session: AsyncSession
    ) -> None:
        sat = await book(session, reservation_date=SATURDAY, start_time=LUNCH_2)
        fri = await book(session, reservation_date=FRIDAY, start_time=DINNER_2)
        cancelled = await book(session, reservation_date=FRIDAY, start_time=LUNCH_1)
        await reservations.cancel_reservation(session, reservation_id=cancelled.id, now=NOW)
        await book(session, phone=phone_number(7))  # someone else

        found = await reservations.find_upcoming_by_phone(
            session, phone="+351 912 345 678", now=NOW
        )

        assert [r.id for r in found] == [fri.id, sat.id]

    async def test_by_phone_skips_sittings_that_already_started(
        self, session: AsyncSession
    ) -> None:
        today_lunch = await book(session, reservation_date=NOW.date(), start_time=LUNCH_1)
        today_dinner = await book(session, reservation_date=NOW.date(), start_time=DINNER_1)
        afternoon = datetime(2026, 10, 14, 15, 0, tzinfo=RESTAURANT_TZ)

        found = await reservations.find_upcoming_by_phone(session, phone="912345678", now=afternoon)

        assert [r.id for r in found] == [today_dinner.id]
        assert today_lunch.id not in [r.id for r in found]

    async def test_by_name_and_date_is_case_insensitive_and_partial(
        self, session: AsyncSession
    ) -> None:
        ana = await book(session, name="Ana Silva", phone=phone_number(1))
        await book(session, name="Rui Costa", phone=phone_number(2))
        await book(session, name="Ana Silva", phone=phone_number(1), reservation_date=SATURDAY)

        found = await reservations.find_upcoming_by_name_and_date(
            session, name="ana", reservation_date=FRIDAY, now=NOW
        )

        assert [r.id for r in found] == [ana.id]


class TestAvailability:
    async def test_full_slot_is_reported_as_fully_booked(self, session: AsyncSession) -> None:
        await book(session, party_size=8, start_time=DINNER_2)

        slots = await reservations.get_availability(
            session, reservation_date=FRIDAY, party_size=8, now=NOW
        )

        assert [(s.start_time, s.available, s.reason) for s in slots] == [
            (LUNCH_1, True, None),
            (LUNCH_2, True, None),
            (DINNER_1, True, None),
            (DINNER_2, False, Rejection.FULLY_BOOKED),
        ]

    async def test_closed_day_and_past_slots_carry_the_rule_reason(
        self, session: AsyncSession
    ) -> None:
        monday = await reservations.get_availability(
            session, reservation_date=MONDAY, party_size=2, now=NOW
        )
        assert {s.reason for s in monday} == {Rejection.CLOSED_DAY}

        half_past_twelve = datetime(2026, 10, 14, 12, 30, tzinfo=RESTAURANT_TZ)
        today = await reservations.get_availability(
            session, reservation_date=NOW.date(), party_size=2, now=half_past_twelve
        )
        assert [s.reason for s in today] == [Rejection.IN_THE_PAST, None, None, None]
