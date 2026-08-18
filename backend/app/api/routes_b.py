from fastapi import APIRouter

from app.modules.agents.router import router as agents_router
from app.modules.suppliers.router import router as suppliers_router
from app.modules.tools.router import router as tools_router

router = APIRouter()
router.include_router(suppliers_router)
router.include_router(agents_router)
router.include_router(tools_router)
