"""Central SQLAlchemy model registry used exclusively by Alembic and metadata checks."""

from app.modules.approval import models as approval_models
from app.modules.audit import models as audit_models
from app.modules.identity import auth_models as identity_auth_models
from app.modules.identity import models as identity_models
from app.modules.inventory import models as inventory_models
from app.modules.invoices import models as invoice_models
from app.modules.master_data import models as master_data_models
from app.modules.orders import models as order_models
from app.modules.procurement import models as procurement_models
from app.modules.receiving import models as receiving_models

__all__ = [
    "identity_auth_models",
    "identity_models",
    "invoice_models",
    "inventory_models",
    "approval_models",
    "audit_models",
    "master_data_models",
    "order_models",
    "procurement_models",
    "receiving_models",
]
