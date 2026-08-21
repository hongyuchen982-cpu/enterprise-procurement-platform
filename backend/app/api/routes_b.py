from fastapi import APIRouter

from app.modules.agents.router import confirmations_router
from app.modules.agents.router import router as agents_router
from app.modules.rag.router import router as rag_router
from app.modules.reporting.router import router as reporting_router
from app.modules.risk.router import router as risk_router
from app.modules.sourcing.router import router as sourcing_router
from app.modules.suppliers.router import router as suppliers_router
from app.modules.tools.router import router as tools_router

router = APIRouter()
router.include_router(suppliers_router)
router.include_router(sourcing_router)
router.include_router(agents_router)
router.include_router(confirmations_router)
router.include_router(rag_router)
router.include_router(risk_router)
router.include_router(reporting_router)
router.include_router(tools_router)
