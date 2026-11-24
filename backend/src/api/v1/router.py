from fastapi import APIRouter, Depends

from api.v1.deps import require_agent, require_viewer
from api.v1.endpoints import (
    agent,
    auth,
    availability,
    calls,
    reservations,
    restaurant,
    voice,
    webhooks,
)

api_router = APIRouter()


# Public.
@api_router.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness check for Render and the dashboard. No auth, no DB."""
    return {"status": "ok"}


api_router.include_router(auth.router)
# No login: every webhook is verified by its ElevenLabs signature instead.
api_router.include_router(webhooks.router)
# No login: hands the website a short-lived ElevenLabs token. Its abuse limits
# (conversations per day, max duration) are the agent's call limits in ElevenLabs.
api_router.include_router(voice.router)

# Dashboard: every route below needs a bearer token, the admin's or a read-only
# guest's. Routes that change data add `require_admin` themselves (guests get 403),
# and guests see phone numbers masked (core/privacy.py).
dashboard = [Depends(require_viewer)]
api_router.include_router(restaurant.router, dependencies=dashboard)
api_router.include_router(availability.router, dependencies=dashboard)
api_router.include_router(reservations.router, dependencies=dashboard)
api_router.include_router(calls.router, dependencies=dashboard)

# Voice agent only: every /agent route needs the X-Agent-Secret header.
api_router.include_router(agent.router, dependencies=[Depends(require_agent)])
