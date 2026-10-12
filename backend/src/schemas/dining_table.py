from pydantic import BaseModel, ConfigDict


class DiningTableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    min_capacity: int
    max_capacity: int
    is_active: bool
