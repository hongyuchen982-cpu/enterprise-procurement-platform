# Local setup

For schema changes and the A/B migration handoff, see [Database migrations](migrations.md).

## Start the stack

1. Copy `.env.example` to `.env`.
2. Replace every `change-*` value with a local-only secret.
3. Run `docker compose config --quiet`.
4. Run `docker compose up --build -d`.
5. Run `docker compose ps` and wait for healthy services.

Useful endpoints:

- Frontend: `http://localhost:5173`
- API liveness: `http://localhost:8000/health/live`
- API readiness: `http://localhost:8000/health/ready`
- Worker health: `http://localhost:8001/health`
- RabbitMQ management: `http://localhost:15672`
- MinIO console: `http://localhost:9001`
- Qdrant API: `http://localhost:6333`

## Verify the skeleton

From the repository root:

```text
ruff check backend
ruff format --check backend
pytest backend
docker compose exec -T api alembic upgrade head
docker compose exec -T api alembic downgrade base
docker compose exec -T api alembic upgrade head
```

From `frontend/`:

```text
npm run lint
npm run typecheck
npm run build
```

No production secrets may be committed to the repository. The committed `.env.example`
contains placeholders only; `.env` is ignored by Git.
