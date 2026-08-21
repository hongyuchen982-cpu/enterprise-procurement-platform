# Purchase orders

Stage 7 implements purchase-order drafts, issuance, and cancellation while preserving the
modular-monolith boundaries. Orders call the procurement and supplier provider facades and never
import their ORM models, repositories, or private services.

## Source and supplier gates

- An order must reference an `APPROVED` procurement request.
- The supplier snapshot must belong to the same organization and be `ACTIVE`, `QUALIFIED`, and
  not frozen.
- Every selected request line category must be present in the supplier qualification categories.
- `sourcing_award_id` is optional until sourcing is implemented. When supplied, it is unique, but
  Stage 7 does not claim to validate an Award that has no authoritative facade yet.

## Split-order allocation

One approved request may be split across multiple purchase orders. Each order line references its
source request line, and the sum of non-cancelled order quantities may not exceed the approved
quantity. The procurement facade locks the request row while allocation is checked and committed,
serializing concurrent split-order creation and updates on MySQL.

Descriptions, specifications, materials, categories, units, currency, and required date are copied
from the approved request. Buyers provide ordered quantities, unit prices, tax rates, and an
optional promised date. `line_amount` and `total_amount` are tax-inclusive and rounded to two
decimal places with `ROUND_HALF_UP`.

## State machine

```text
DRAFT --issue--> ISSUED --cancel before fulfillment--> CANCELLED
  |                  |
  +--delete/update---+ (update/delete are DRAFT-only)
```

The schema reserves `PARTIALLY_RECEIVED`, `RECEIVED`, and `CLOSED` for the receiving and invoice
stages. Cancellation is rejected after any received or invoiced quantity exists. Every mutation
requires `expected_version` optimistic concurrency control.

## Permissions and data scope

Migration `0009_purchase_orders` seeds:

- `order.read`
- `order.create`
- `order.update`
- `order.issue`
- `order.cancel`

API authorization evaluates the request organization, department, owner, and every source line
category. List endpoints filter inaccessible orders rather than leaking their existence.

## API and persistence

- `POST /api/v1/purchase-orders`
- `GET /api/v1/purchase-orders?organization_id=...`
- `GET /api/v1/purchase-orders/{order_id}`
- `PUT /api/v1/purchase-orders/{order_id}`
- `DELETE /api/v1/purchase-orders/{order_id}?expected_version=...`
- `POST /api/v1/purchase-orders/{order_id}/issue`
- `POST /api/v1/purchase-orders/{order_id}/cancel`

`purchase_orders` stores the lifecycle and source/supplier references. `purchase_order_lines`
stores immutable source attributes, allocation quantities, fulfillment counters, prices, tax, and
tax-inclusive amounts. Supplier and Award identifiers intentionally have no database foreign keys
because their provider-owned persistence is outside the orders module and Award persistence is not
implemented.
