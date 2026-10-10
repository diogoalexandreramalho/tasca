"""ORM models. Import each model module here so Alembic autogenerate sees it."""

from models.booking_slot import BookingSlot, Service
from models.customer import Customer
from models.dining_table import DiningTable
from models.reservation import Reservation, ReservationStatus

__all__ = [
    "BookingSlot",
    "Customer",
    "DiningTable",
    "Reservation",
    "ReservationStatus",
    "Service",
]
