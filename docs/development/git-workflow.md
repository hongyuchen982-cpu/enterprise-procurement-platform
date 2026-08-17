# Git workflow

- `main` is always releasable and accepts release or urgent-fix pull requests.
- `develop` is the integration branch.
- Feature branches use `feature/a-*` and `feature/b-*`.
- Fix branches use `fix/a-*` and `fix/b-*`.
- Direct pushes and force pushes to `main` and `develop` are forbidden.
- Feature pull requests are squash merged after one review and required checks.
- Shared-file changes must be explicitly identified in the pull-request description.
- Migrations are integrated and merged by member A only.
