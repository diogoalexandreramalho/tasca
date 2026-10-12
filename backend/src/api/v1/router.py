from fastapi import APIRouter, Depends

from api.v1.deps import require_admin
from api.v1.endpoints import auth, availability, meta, reservations, restaurant

api_router = APIRouter()

# Public.
api_router.include_router(meta.router)
api_router.include_router(auth.router)

# Admin only: every route below needs a valid bearer token.
admin = [Depends(require_admin)]
api_router.include_router(restaurant.router, dependencies=admin)
api_router.include_router(availability.router, dependencies=admin)
api_router.include_router(reservations.router, dependencies=admin)
