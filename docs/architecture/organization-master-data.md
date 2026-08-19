# Organization and master data

Stage 4 completes the organization and procurement master-data foundation used by later
procurement requests, approvals, orders, receiving, and invoice matching.

## Ownership and boundaries

- Identity owns the persisted organization tree, users, memberships, roles, permissions,
  and data scopes.
- The organizations module exposes HTTP routes but reaches organization persistence only
  through `IdentityFacade`.
- Master data owns categories, units, and materials. Other business modules consume
  `MasterDataFacade` or immutable contracts and must not import its models or repository.
- Organization references use `iam_organizations.id`; category and material codes are unique
  within an organization, while unit codes are global.

## Authorization

All organization and master-data routes require a bearer token and `X-Membership-ID` header.
The selected membership must belong to the authenticated user. Access is then evaluated by
the existing permission and data-scope engine.

Permission codes seeded by migration `0004_organization_master_data`:

- `organization.read`
- `organization.manage`
- `master_data.read`
- `master_data.manage`

Organization and master-data administrators should receive an `ORGANIZATION` or
`ORGANIZATION_TREE` scope. Material authorization includes both organization and category
dimensions so a category-specific grant can be used where required.

## API surface

- `GET /api/v1/organizations/{organization_id}/tree`
- `POST /api/v1/organizations`
- `POST /api/v1/organizations/memberships`
- `GET|POST /api/v1/master-data/categories`
- `GET|POST /api/v1/master-data/units`
- `GET|POST /api/v1/master-data/materials`

The access-evaluation endpoint also requires authentication and rejects attempts to inspect
a membership belonging to another user.

## Data invariants

- Organization codes are globally unique and normalized to uppercase.
- A membership department must be inside its organization tree.
- Category parents must belong to the same organization.
- Material categories must belong to the material organization.
- Materials may reference only active units and active categories.
- Formal records use optimistic versions and soft deletion.
