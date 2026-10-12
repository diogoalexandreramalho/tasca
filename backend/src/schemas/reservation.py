import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from models import ReservationStatus
from schemas.booking_slot import BookingSlotRead


class ReservationCreate(BaseModel):
    reservation_date: date
    start_time: time = Field(description="Start of a sitting, e.g. 20:30.")
    party_size: int
    customer_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(max_length=32, description="Any format; national numbers default to PT.")
    notes: str | None = Field(
        default=None, max_length=1000, description='Allergies start with "Alergia:".'
    )


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str


class ReservationTableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_date: date
    party_size: int
    status: ReservationStatus
    notes: str | None
    customer: CustomerRead
    table: ReservationTableRead
    booking_slot: BookingSlotRead
    created_at: datetime
    updated_at: datetime
