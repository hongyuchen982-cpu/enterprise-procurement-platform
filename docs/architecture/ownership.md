# Ownership

## Member A

Identity, organizations, RBAC/data scope, master data, procurement, approval, orders, receiving, inventory-lite, invoices, audit, database foundation, Alembic integration, and shared merge ownership unless explicitly assigned otherwise.

## Member B

Suppliers, sourcing, agents, tools, RAG, risk, reporting, messaging/worker, object storage, vector store, and LLM infrastructure.

## Shared rules

- Shared files have one merge owner.
- A feature PR should not modify the other member's module internals.
- Contract providers own their domain contract; consumers review compatibility.
- Member A is the only Alembic migration integrator.
- CODEOWNERS placeholders must be replaced with real GitHub usernames before repository protection is enabled.
