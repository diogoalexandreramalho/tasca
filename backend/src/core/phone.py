import phonenumbers

from core.exceptions import ValidationAppError

DEFAULT_REGION = "PT"


def normalize_phone(raw: str) -> str:
    """Return the number in E.164 (e.g. +351912345678). National numbers default to Portugal."""
    try:
        number = phonenumbers.parse(raw, DEFAULT_REGION)
    except phonenumbers.NumberParseException as exc:
        raise ValidationAppError("Invalid phone number.", details={"phone": raw}) from exc
    if not phonenumbers.is_valid_number(number):
        raise ValidationAppError("Invalid phone number.", details={"phone": raw})
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
