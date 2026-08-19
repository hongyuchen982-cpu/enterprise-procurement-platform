# Database migrations

Member A (`@hongyuchen982-cpu`) is the sole Alembic migration integrator. Member B owns
their SQLAlchemy models but hands migration requirements to A for integration. The migration
graph must always have exactly one head.

## Model conventions

- Formal entities use UUID primary keys.
- Persisted timestamps are UTC-aware in Python and use database defaults for creation.
- Mutable formal entities use the SQLAlchemy version column for optimistic concurrency.
- Soft deletion is opt-in and repositories must explicitly exclude `deleted_at` rows.
- Constraints and indexes use the naming convention defined in `app.core.database`.
- Every business module is imported by `app.models`; Alembic imports only that registry.

## Creating a migration

From `backend/`:

```shell
alembic current
alembic heads
alembic revision --autogenerate -m "short description"
alembic check
```

Review generated migrations manually. Autogenerate cannot decide data backfills, safe lock
duration, online index strategy, or whether a destructive change is acceptable.

## Required verification

Every migration pull request must pass:

```shell
alembic upgrade head
alembic check
alembic downgrade base
alembic upgrade head
python -m pytest tests/database tests/architecture
```

CI performs the round trip against MySQL. The test suite also performs a lightweight SQLite
round trip to catch broken revision graphs and missing model registration early.

## B-to-A handoff

Member B provides:

1. the model diff and business reason;
2. proposed table, column, index, and constraint changes;
3. backfill or compatibility requirements;
4. expected downgrade behavior;
5. evidence that existing consumers remain compatible.

Member A rebases onto the current migration head, generates or integrates the revision,
resolves conflicts, runs the full round trip, and owns the final migration file.

## Safety rules

- Never edit a migration that has reached a shared branch; add a new revision instead.
- Never create parallel heads without an explicit A-owned merge revision.
- Destructive changes use expand-and-contract across separate deployable revisions.
- Data backfills must be restartable and bounded; large backfills do not run as one DDL
  transaction.
- Downgrade must restore schema shape. If data recovery is impossible, document that fact and
  provide a forward-fix plan before review.
