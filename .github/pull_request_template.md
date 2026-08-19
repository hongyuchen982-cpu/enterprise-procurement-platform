## Scope

- Delivery lane: A / B
- CODEOWNER: @hongyuchen982-cpu / @cannjin197-netizen
- Modules changed:
- Why this change is needed:

- [ ] Branch follows the protected-branch flow documented in `docs/development/git-workflow.md`
- [ ] Changes stay inside the selected delivery lane
- [ ] No other module's models, repositories, services, or database session are imported

## Contracts and shared files

- [ ] No contract changed
- [ ] Contract change is backward compatible and reviewed by both members
- [ ] Shared files changed are listed below with their unique owner

Shared files changed:

## Database and messaging

- [ ] No migration
- [ ] Migration is authored or integrated by @hongyuchen982-cpu
- [ ] Migration follows `docs/development/migrations.md` and has one Alembic head
- [ ] No event contract changed
- [ ] Event consumers are idempotent, or this PR has no event consumer changes

## Verification

- [ ] Backend lint and format checks
- [ ] Backend tests
- [ ] Architecture boundary tests
- [ ] Frontend lint, typecheck, and build
- [ ] Compose/config validation where relevant

## Risk and rollback

- Risk level: low / medium / high
- Rollback or forward-fix plan:
