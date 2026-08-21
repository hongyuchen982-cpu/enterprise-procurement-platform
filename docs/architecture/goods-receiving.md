# Goods receiving

Stage 8 implements receipt drafts, line inspection, completion, and cancellation. Receiving calls
the orders facade synchronously; both modules share one SQLAlchemy session so receipt completion
and purchase-order fulfillment commit or roll back atomically.

## State and inspection rules

```text
DRAFT --complete inspections--> COMPLETED
  |
  +--cancel--> CANCELLED
  +--delete
```

- Only `ISSUED` or `PARTIALLY_RECEIVED` purchase orders accept receipt drafts.
- Draft receipt lines may remain `PENDING`; completion requires every inspection to be resolved.
- `FAILED` lines cannot contain accepted quantity. `PASSED` lines require accepted quantity.
- A line's physical received quantity equals accepted plus rejected quantity and must be positive.
- Completed receipts are immutable. Cancellation and deletion are draft-only, so posted order
  quantities never require silent reversal.

## Order fulfillment

Only accepted quantity increments `purchase_order_lines.received_quantity`. Rejected quantity is
retained on the receipt for audit but does not fulfill the order. An order becomes
`PARTIALLY_RECEIVED` after a partial accepted receipt and `RECEIVED` when every order line is fully
accepted.

The orders facade locks the purchase-order aggregate before checking and applying accepted
quantities. Concurrent receipt completions therefore cannot make cumulative accepted quantity
exceed ordered quantity on MySQL.

## Identity, permissions, and data scope

Every receipt records the authenticated receiver membership and user. The membership must be
active, belong to the user, and match the order organization. Migration `0010_goods_receiving`
seeds:

- `receipt.read`
- `receipt.create`
- `receipt.update`
- `receipt.complete`
- `receipt.cancel`

Authorization follows the source procurement request's organization, department, owner, and every
line category. List endpoints filter inaccessible receipts.

## API and persistence

- `POST /api/v1/receipts`
- `GET /api/v1/receipts?organization_id=...`
- `GET /api/v1/receipts/{receipt_id}`
- `PUT /api/v1/receipts/{receipt_id}`
- `DELETE /api/v1/receipts/{receipt_id}?expected_version=...`
- `POST /api/v1/receipts/{receipt_id}/complete`
- `POST /api/v1/receipts/{receipt_id}/cancel`

`goods_receipts` owns the lifecycle, receiver, order, and completion timestamp.
`goods_receipt_lines` owns inspection results and balanced physical, accepted, and rejected
quantities. Database checks enforce status, inspection, positivity, and quantity-balance rules.
