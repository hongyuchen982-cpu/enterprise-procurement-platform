# Local setup

The executable skeleton will support the following flow after bootstrap completion:

1. Copy `.env.example` to `.env` and replace local-only placeholder secrets.
2. Run `docker compose up --build -d`.
3. Inspect `docker compose ps`.
4. Open the frontend and health page.
5. Verify `GET /health/live` and `GET /health/ready`.

No production secrets may be committed to the repository.
