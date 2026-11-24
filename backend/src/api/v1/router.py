from fastapi import APIRouter, Depends

from api.v1.deps import require_admin, require_agent
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

# Admin only: every route below needs a valid bearer token.
admin = [Depends(require_admin)]
api_router.include_router(restaurant.router, dependencies=admin)
api_router.include_router(availability.router, dependencies=admin)
api_router.include_router(reservations.router, dependencies=admin)
api_router.include_router(calls.router, dependencies=admin)

# Voice agent only: every /agent route needs the X-Agent-Secret header.
api_router.include_router(agent.router, dependencies=[Depends(require_agent)])
