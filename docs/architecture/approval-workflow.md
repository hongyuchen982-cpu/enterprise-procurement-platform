# Approval workflow

Stage 6 adds reusable sequential approval templates and transactional procurement-request
state transitions. Sourcing publication and outbox events remain later stages.

## Ownership and boundaries

- Approval owns templates, copied instance nodes, current-step progression, immutable action
  records, decisions, transfers, and cancellation rules.
- Procurement owns request status. Approval changes it only through `ProcurementFacade`.
- Identity owns active memberships, permissions, and data scopes. Approval never imports
  Identity or Procurement models/repositories.
- Starting or completing approval commits approval and procurement changes through the same
  SQLAlchemy session, so partial workflow state cannot be persisted.

## Workflow

```text
request SUBMITTED
       |
       v
approval PENDING: node 1 -> node 2 -> ... -> node N
       |                                  |
       | reject                           | all approve
       v                                  v
request REJECTED                   request APPROVED
```

- Only one approval instance may exist for a procurement request.
- Starting approval copies every template step into immutable, ordered instance nodes and
  stores the submitted procurement snapshot.
- Only the active membership assigned to the current node may approve, reject, or transfer.
- Rejection requires a non-empty comment and skips all later nodes.
- Transfer changes the current assignee and writes an immutable `TRANSFER` action.
- Approval can be cancelled only before the first approve/reject/transfer action. Cancellation
  skips every node and returns the procurement request to `SUBMITTED`.
- All instance mutations require `expected_version` optimistic concurrency control.

## Permissions

Migration `0006_approval_workflow` seeds:

- `approval.template.manage`
- `approval.instance.start`
- `approval.instance.read`
- `approval.task.decide`

Every API requires bearer authentication and `X-Membership-ID`. Request-related access is
evaluated against organization, department, requester, and every line category. Assignment
validation is enforced in addition to permission/data-scope validation.

## API surface

- `POST /api/v1/approval-templates`
- `GET /api/v1/approval-templates?organization_id=...`
- `POST /api/v1/approvals`
- `GET /api/v1/approvals?organization_id=...`
- `GET /api/v1/approvals/{instance_id}`
- `POST /api/v1/approvals/{instance_id}/decisions`
- `POST /api/v1/approvals/{instance_id}/transfers`
- `POST /api/v1/approvals/{instance_id}/cancel`

## Persistence

- `approval_templates` and `approval_template_steps` define reusable workflows.
- `approval_instances` stores status, current step, request version, and submitted snapshot.
- `approval_nodes` stores copied assignments and final node outcomes.
- `approval_actions` records every approve, reject, and transfer action.
- Migration downgrade maps approval-owned request states back to `SUBMITTED` before restoring
  the Stage 5 request-status constraint.
