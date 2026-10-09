from fastapi import APIRouter

from api.v1.endpoints import meta

api_router = APIRouter()
api_router.include_router(meta.router)
