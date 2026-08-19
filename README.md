# Enterprise Procurement Platform

企业采购与供应链智能协同平台，采用模块化单体架构，由两名成员按业务域纵向协作开发。

当前仓库阶段：工程治理、数据库底座、身份认证、IAM/RBAC、组织树与采购主数据底座
已实现。采购申请、审批、订单、收货、发票、寻源、RAG 和 Agent 完整业务链尚未实现。

## Frozen stack

- FastAPI, SQLAlchemy 2, Alembic, MySQL
- Vue 3, TypeScript, Vite, Pinia, Vue Router, Element Plus
- Redis, RabbitMQ, MinIO, Qdrant
- Independent worker, RAG, Agent Orchestrator, Tool Registry
- Docker Compose

## Ownership

- Member A: identity, organizations, RBAC/Data Scope, master data, procurement, approval, orders, receiving, inventory-lite, invoices, audit.
- Member B: suppliers, sourcing, agents, tools, RAG, risk, reporting, messaging/worker, object storage, vector store, LLM infrastructure.
- Shared files always have one merge owner. See [ownership](docs/architecture/ownership.md).

组织与采购主数据的边界、权限和 API 约定见
[organization and master data](docs/architecture/organization-master-data.md)。

## Branches

- `main`: always releasable.
- `develop`: integration branch.
- `feature/a-*`, `feature/b-*`: feature work.
- `fix/a-*`, `fix/b-*`: fixes.

## Start locally

1. Copy `.env.example` to `.env` and replace the local-only placeholder secrets.
2. Run `docker compose up --build -d`.
3. Run `docker compose ps` and wait until the services are healthy.
4. Open the frontend at `http://localhost:5173`.

API liveness is exposed at `GET http://localhost:8000/health/live`; readiness is at
`GET http://localhost:8000/health/ready`. RabbitMQ management, MinIO console, and the
worker health endpoint use ports `15672`, `9001`, and `8001` respectively.

See [local setup](docs/development/local-setup.md) for verification commands.
