# Procurement requests

Stage 5 implements Member A's procurement-request draft and submission boundary. Approval,
sourcing publication, and transactional outbox delivery remain later stages.

## Ownership and boundaries

- The procurement module owns request headers, lines, state transitions, numbering, and
  server-calculated estimated amounts.
- Identity provides the authenticated membership, requester user ID, permissions, and data
  scopes through `IdentityFacade`.
- Organization, category, material, and unit references are consumed as foreign keys and
  validated through their public domain records. Procurement does not mutate master data.
- The immutable `ProcurementRequestSnapshot` contract is the future handoff boundary for
  approval and B-owned sourcing.

## State machine

```text
DRAFT --submit--> SUBMITTED --start approval--> IN_APPROVAL
  ^                   |                            |
  +-----withdraw------+                 +----------+----------+
                                           approve | reject
                                                   v
                                           APPROVED/REJECTED
```

- Only `DRAFT` requests can be edited or soft-deleted.
- A submitted request cannot be edited or deleted.
- Withdrawal returns a submitted request to `DRAFT` but is rejected after approval starts.
- An approval may be cancelled before its first action, returning the request to `SUBMITTED`;
  the requester may then use the normal withdrawal operation.
- Every mutation supplies `expected_version`; stale clients receive a conflict response.

## Permissions and data scope

Migration `0005_procurement_requests` seeds:

- `procurement.request.read`
- `procurement.request.create`
- `procurement.request.update`
- `procurement.request.submit`

All routes require a bearer token and `X-Membership-ID`. The membership must belong to the
authenticated user. Permission and data-scope evaluation is applied to the organization,
department, requester, and every line category. This supports organization, organization-tree,
department, self, and category-scoped buyers without bypassing line-level scope restrictions.

## API surface

- `POST /api/v1/procurement-requests`
- `GET /api/v1/procurement-requests?organization_id=...`
- `GET /api/v1/procurement-requests/{request_id}`
- `PUT /api/v1/procurement-requests/{request_id}`
- `DELETE /api/v1/procurement-requests/{request_id}?expected_version=...`
- `POST /api/v1/procurement-requests/{request_id}/submit`
- `POST /api/v1/procurement-requests/{request_id}/withdraw`

## Data invariants

- Request organization must equal the active requester membership organization.
- Department must be the organization itself or an active descendant.
- Required date cannot be in the past when a request is created, updated, or submitted.
- Each request has 1 to 200 lines through the API.
- Category must be active and belong to the request organization.
- If a material is supplied, its organization, category, and unit must match the line.
- Quantity is positive; estimated unit price is optional and non-negative.
- Line amounts and request totals are calculated on the server using decimal arithmetic and
  rounded to two currency decimals with `ROUND_HALF_UP`.
- Request numbers use `PR-YYYYMMDD-<12 hex characters>` and are unique.
- Deletion is soft deletion so later audit work can preserve formal history.
