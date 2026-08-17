from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.routes_a import router as routes_a
from app.api.routes_b import router as routes_b

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(routes_a)
api_router.include_router(routes_b)
