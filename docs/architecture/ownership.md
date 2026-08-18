# Ownership

## Member A

`@hongyuchen982-cpu` owns identity, organizations, RBAC/data scope, master data,
procurement, approval, orders, receiving, inventory-lite, invoices, audit, database
foundation, Alembic integration, and shared merge ownership unless explicitly assigned
otherwise.

## Member B

`@cannjin197-netizen` owns suppliers, sourcing, agents, tools, RAG, risk, reporting,
messaging/worker, object storage, vector store, and LLM infrastructure.

## Shared rules

- Shared files have one merge owner.
- A feature PR should not modify the other member's module internals.
- Contract providers own their domain contract; consumers review compatibility.
- `@hongyuchen982-cpu` is the only Alembic migration integrator.
- Unlisted paths use `@hongyuchen982-cpu` as the default shared-file merge owner.
- Repository protection must require the `backend`, `frontend`, and `compose-config` checks.
