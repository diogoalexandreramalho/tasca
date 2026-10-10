from sqlalchemy import Boolean, CheckConstraint, SmallInteger, String, true
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


class DiningTable(Base, TimestampMixin):
    __tablename__ = "dining_tables"
    __table_args__ = (
        CheckConstraint("min_capacity >= 1", name="min_capacity_positive"),
        CheckConstraint("min_capacity <= max_capacity", name="capacity_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    min_capacity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    max_capacity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
