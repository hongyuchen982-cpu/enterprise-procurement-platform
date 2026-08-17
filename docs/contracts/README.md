# Contracts

Pydantic contract models live under `backend/app/contracts`. Contracts must not import SQLAlchemy ORM models or repositories. Common envelopes are shared-owned; domain snapshots are owned by their provider and reviewed by consumers.
