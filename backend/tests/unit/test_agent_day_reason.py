import pytest

from api.v1.endpoints.agent import day_reason
from services.booking_rules import Rejection

R = Rejection


@pytest.mark.parametrize(
    ("reasons", "expected"),
    [
        # Something the caller can act on wins over "fully booked".
        ([R.PARTY_SIZE_OUT_OF_RANGE] * 4, R.PARTY_SIZE_OUT_OF_RANGE),
        ([R.CLOSED_DAY] * 4, R.CLOSED_DAY),
        ([R.TOO_FAR_AHEAD] * 4, R.TOO_FAR_AHEAD),
        ([R.IN_THE_PAST] * 4, R.IN_THE_PAST),
        # Later today: lunch started, 19:00 is under an hour away, 20:30 is full.
        ([R.IN_THE_PAST, R.IN_THE_PAST, R.TOO_SOON, R.FULLY_BOOKED], R.FULLY_BOOKED),
        ([R.FULLY_BOOKED] * 4, R.FULLY_BOOKED),
    ],
)
def test_day_reason_picks_the_actionable_explanation(
    reasons: list[Rejection], expected: Rejection
) -> None:
    assert day_reason(reasons) is expected
