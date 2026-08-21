# Inventory-lite and formal audit

Stage 10 closes the Member A delivery with a receipt-derived inventory ledger and an immutable
formal audit trail for accounting-impacting actions.

## Inventory-lite boundary

Inventory-lite deliberately implements only authoritative inbound stock:

- completing a receipt posts accepted quantity for material-backed order lines;
- rejected quantities and free-text/service lines do not enter inventory;
- one balance exists per organization and material;
- each accepted receipt line creates one immutable `RECEIPT` movement;
- the source-type/source-line uniqueness constraint makes posting idempotent;
- balance and movement use the material's copied category and unit for data-scope checks.

The inventory balance is locked and refreshed before update. Inventory staging, receipt completion,
the order's received counter, and the audit record share one SQLAlchemy transaction. A failure in
any part rolls back all four representations.

Outbound issues, transfers, reservations, valuation, and warehouses are outside inventory-lite and
must not be inferred from `on_hand_quantity` until a later inventory expansion explicitly models
them.

## Formal audit trail

`business_audit_log` is append-only through the application API. It records organization, action,
business object and version, actor membership/user/type, source, before/after evidence, and
occurrence time. Stage 10 atomically records the two formal posting boundaries:

- `RECEIPT_COMPLETED`
- `INVOICE_APPROVED`

Existing approval actions remain the immutable detailed trail for approve/reject/transfer steps;
authentication security events remain in the authentication subsystem. This avoids duplicating
domain-specific evidence while providing one queryable accounting-impact trail.

## Permissions and APIs

Migration `0010_inventory_audit` seeds `inventory.read` and `audit.read`.

- `GET /api/v1/inventory/balances?organization_id=...`
- `GET /api/v1/inventory/movements?organization_id=...&material_id=...`
- `GET /api/v1/audit-log?organization_id=...&object_type=...&object_id=...&action=...`

Inventory queries apply organization and category data scope. Audit queries require organization
scope and can filter by action or business object without exposing inaccessible organizations.

## Final Member A acceptance

The formal synchronous chain is now:

```text
request -> approval -> purchase order -> inspected receipt
        -> inventory receipt ledger -> invoice matching -> order close
        -> formal audit evidence
```

Each mutable aggregate uses optimistic locking, cross-aggregate accounting writes use a shared
transaction, and MySQL constraints protect statuses, quantities, monetary values, uniqueness, and
source idempotency. Supplier and sourcing persistence, asynchronous outbox delivery, RAG, and Agent
execution remain provider-owned Member B work and are not simulated in the Member A modules.
