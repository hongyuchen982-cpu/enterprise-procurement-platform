"""Central SQLAlchemy model registry used exclusively by Alembic and metadata checks."""

from app.modules.identity import auth_models as identity_auth_models
from app.modules.identity import models as identity_models
from app.modules.master_data import models as master_data_models
from app.modules.risk import models as b_risk_models
from app.modules.sourcing import models as b_sourcing_models
from app.modules.suppliers import models as b_supplier_models
from app.persistence import agent_models as b_agent_models
from app.persistence import rag_models as b_rag_models

__all__ = [
    "b_agent_models",
    "b_rag_models",
    "b_risk_models",
    "b_sourcing_models",
    "b_supplier_models",
    "identity_auth_models",
    "identity_models",
    "master_data_models",
]
