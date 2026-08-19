# Git workflow

- `main` is always releasable and accepts release or urgent-fix pull requests.
- `develop` is the integration branch.
- Feature branches use `feature/a-*` and `feature/b-*`.
- Fix branches use `fix/a-*` and `fix/b-*`.
- Emergency fixes targeting `main` use `hotfix/a-*` and `hotfix/b-*`.
- Normal releases are pull requests from `develop` to `main`.
- Direct pushes and force pushes to `main` and `develop` are forbidden.
- Feature pull requests are squash merged after one review and required checks.
- Shared-file changes must be explicitly identified in the pull-request description.
- Migrations are integrated and merged by member A only.

## Pull-request gates

Every pull request must:

1. Select exactly one delivery lane, A or B.
2. Stay within that lane's module internals.
3. List every shared file and its unique merge owner.
4. Obtain one approval from the other member; the affected CODEOWNER remains the merge owner.
5. Pass the `backend`, `frontend`, and `compose-config` checks.
6. Use squash merge so the integration branches keep one commit per pull request.

## GitHub branch protection

Configure both `main` and `develop` rulesets with:

- pull requests required before merging;
- one approving review from someone other than the pull-request author;
- stale approvals dismissed when new commits are pushed;
- approval required for the most recent reviewable push;
- all conversations resolved before merging;
- required checks: `backend`, `frontend`, and `compose-config`;
- force pushes and branch deletion blocked;
- administrators included, with bypass limited to emergency recovery.

Repository settings are external state. Updating these files does not enable the ruleset;
an administrator must apply this checklist in GitHub after the governance pull request merges.

### Two-person CODEOWNERS limitation

Each current CODEOWNERS rule intentionally names one merge owner. Because GitHub does not
allow an author to approve their own pull request, enabling "Require review from Code Owners"
would deadlock an owner working in their own lane. Keep that setting disabled while the team
has only one eligible owner per rule. CODEOWNERS still documents ownership and requests the
right reviewer; the required approval must come from the other member. Enable the hard Code
Owner requirement only after each protected area names a second eligible owner or an
appropriate GitHub Team.
