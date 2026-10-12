from datetime import time

from pydantic import BaseModel, ConfigDict

from models import Service


class BookingSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service: Service
    start_time: time
    end_time: time
