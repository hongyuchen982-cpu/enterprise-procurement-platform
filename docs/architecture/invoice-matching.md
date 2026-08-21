# Invoice matching

Stage 9 implements supplier-invoice drafts, three-way matching, exception approval, and atomic
purchase-order invoicing. Invoices call the orders facade and never import order persistence
internals.

## State machine

```text
DRAFT --submit/match--> MATCHED ----approve----> APPROVED
                   \--> EXCEPTION --approve with comment--> APPROVED

DRAFT | MATCHED | EXCEPTION --cancel--> CANCELLED
```

Only drafts may be edited or deleted. Approved invoices are immutable and cannot be cancelled.
Every mutation requires `expected_version` optimistic concurrency control.

## Three-way matching

Each invoice belongs to one purchase order and supplier. Supplier and currency must match the
order. Invoice lines reference order lines and are unique within an invoice.

Submission evaluates:

- quantity: current approved invoice quantity plus this invoice must not exceed accepted receipt
  quantity;
- unit price: invoice and order prices may differ by at most `0.01`;
- tax: invoice and order tax rates must be equal.

Every line stores quantity and price match results. All results must pass for invoice status
`MATCHED`; any failure produces `EXCEPTION`. Tax-inclusive line and invoice amounts use
`ROUND_HALF_UP` to two decimal places.

## Approval and order closure

Approval writes the invoice and order counters through the same SQLAlchemy session. The orders
facade locks and refreshes the aggregate before applying invoice quantities, preventing concurrent
matched invoices from consuming the same accepted quantity. Exception invoices may exceed normal
quantity or price rules only with an explicit approval comment.

An order becomes `CLOSED` once every line is fully accepted and cumulative approved invoice
quantity is at least the ordered quantity. This check runs after either receipt completion or
invoice approval, so out-of-order exception processing still converges to the correct state.

## Permissions, API, and persistence

Migration `0009_invoice_matching` seeds `invoice.read`, `invoice.create`, `invoice.update`,
`invoice.submit`, `invoice.approve`, and `invoice.cancel`. Authorization follows the source
procurement request's organization, department, owner, and categories.

- `POST /api/v1/invoices`
- `GET /api/v1/invoices?organization_id=...`
- `GET /api/v1/invoices/{invoice_id}`
- `PUT /api/v1/invoices/{invoice_id}`
- `DELETE /api/v1/invoices/{invoice_id}?expected_version=...`
- `POST /api/v1/invoices/{invoice_id}/submit`
- `POST /api/v1/invoices/{invoice_id}/approve`
- `POST /api/v1/invoices/{invoice_id}/cancel`

`supplier_invoices` owns supplier identity, legal invoice number, lifecycle, totals, and approval
evidence. `supplier_invoice_lines` owns order-line references, invoice quantities/prices/tax,
amounts, and matching results. Supplier identifiers intentionally have no database foreign key
because supplier persistence belongs to Member B.
