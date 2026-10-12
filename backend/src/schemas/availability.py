from datetime import time

from pydantic import BaseModel, ConfigDict

from models import Service
from services.booking_rules import Rejection


class SlotAvailabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service: Service
    start_time: time
    end_time: time
    available: bool
    reason: Rejection | None
