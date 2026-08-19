"""Central SQLAlchemy model registry used exclusively by Alembic and metadata checks."""

from app.modules.identity import auth_models as identity_auth_models
from app.modules.identity import models as identity_models

__all__ = ["identity_auth_models", "identity_models"]
