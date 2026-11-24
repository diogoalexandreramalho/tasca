"""Hiding phone numbers from read-only guests (the public dashboard demo).

Guests see what website visitors said, so phone numbers are masked: the
customer's phone field, and anything in free text that looks like one. Times
("20:30"), dates and party sizes stay readable. Numbers spoken as words
("nine one two…") are not caught; that's an accepted limit of the demo.
"""

import re

import phonenumbers

MASK = "•"

# 6+ digits, optionally separated by spaces, dots or brackets: "912 345 678",
# "+351 912.345.678". Not "20:30" (colon) or "4 people".
_PHONE_LIKE = re.compile(r"\+?\d(?:[ .()]*\d){5,}")


def mask_phone(phone: str) -> str:
    """'+351912345678' → '+351•••••••78': country code and last two digits only."""
    try:
        prefix = f"+{phonenumbers.parse(phone).country_code}"
    except phonenumbers.NumberParseException:
        prefix = ""
    rest = phone.removeprefix(prefix)
    if len(rest) <= 2:
        return prefix + MASK * len(rest)
    return prefix + MASK * (len(rest) - 2) + rest[-2:]


def mask_phone_numbers(text: str) -> str:
    """Mask every digit of anything in `text` that looks like a phone number."""
    return _PHONE_LIKE.sub(lambda m: re.sub(r"\d", MASK, m.group()), text)
