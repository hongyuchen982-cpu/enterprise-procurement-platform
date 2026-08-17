from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.lifespan import lifespan
from app.core.request_context import RequestContextMiddleware
from app.core.settings.base import get_base_settings

settings = get_base_settings()
app = FastAPI(title="Enterprise Procurement Platform", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)
app.include_router(api_router)
