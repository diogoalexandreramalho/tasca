from fastapi import APIRouter, Depends

from api.v1.deps import require_admin, require_agent
from api.v1.endpoints import agent, auth, availability, meta, reservations, restaurant

api_router = APIRouter()

# Public.
api_router.include_router(meta.router)
api_router.include_router(auth.router)

# Admin only: every route below needs a valid bearer token.
admin = [Depends(require_admin)]
api_router.include_router(restaurant.router, dependencies=admin)
api_router.include_router(availability.router, dependencies=admin)
api_router.include_router(reservations.router, dependencies=admin)

# Voice agent only: every /agent route needs the X-Agent-Secret header.
api_router.include_router(agent.router, dependencies=[Depends(require_agent)])
