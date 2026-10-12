from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session

DbSession = Annotated[AsyncSession, Depends(get_session)]


def get_now() -> datetime:
    """The current time. A dependency so tests can pin it (see `app.dependency_overrides`)."""
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(get_now)]
