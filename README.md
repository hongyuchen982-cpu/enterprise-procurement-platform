# Enterprise Procurement Platform

企业采购与供应链智能协同平台，采用模块化单体架构，由两名成员按业务域纵向协作开发。

当前仓库阶段：工程骨架与基础设施初始化。尚未实现采购、供应商、寻源、订单、发票、RAG 或 Agent 业务逻辑。

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

## Branches

- `main`: always releasable.
- `develop`: integration branch.
- `feature/a-*`, `feature/b-*`: feature work.
- `fix/a-*`, `fix/b-*`: fixes.

Local setup and verification commands will be documented in [local setup](docs/development/local-setup.md) as the skeleton is added.
