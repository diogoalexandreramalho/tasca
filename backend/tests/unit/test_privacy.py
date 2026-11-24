import pytest

from core.privacy import mask_phone, mask_phone_numbers


@pytest.mark.parametrize(
    ("phone", "masked"),
    [
        ("+351912345678", "+351•••••••78"),
        ("+447911123456", "+44••••••••56"),
        ("912345678", "•••••••78"),  # not E.164: no country code to keep
        ("12", "••"),
    ],
)
def test_mask_phone_keeps_country_code_and_last_two_digits(phone: str, masked: str) -> None:
    assert mask_phone(phone) == masked


@pytest.mark.parametrize(
    ("text", "masked"),
    [
        ("My number is 912 345 678.", "My number is ••• ••• •••."),
        ("Call +351 912.345.678 please", "Call +••• •••.•••.••• please"),
        ("It's 912345678", "It's •••••••••"),
    ],
)
def test_masks_phone_numbers_in_text(text: str, masked: str) -> None:
    assert mask_phone_numbers(text) == masked


@pytest.mark.parametrize(
    "text",
    [
        "A table for 4 at 20:30 on the 13th.",
        "Friday the 6th of November, 2026.",
        "Booking for 8 people, 12:00 or 13:30.",
        "nine one two, three four five",  # spoken words: a known, accepted gap
    ],
)
def test_leaves_times_dates_and_sizes_alone(text: str) -> None:
    assert mask_phone_numbers(text) == text
