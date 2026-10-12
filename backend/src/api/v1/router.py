from fastapi import APIRouter

from api.v1.endpoints import availability, meta, reservations, restaurant

api_router = APIRouter()
api_router.include_router(meta.router)
api_router.include_router(restaurant.router)
api_router.include_router(availability.router)
api_router.include_router(reservations.router)
