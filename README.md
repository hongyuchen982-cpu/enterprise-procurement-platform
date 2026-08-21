# Enterprise Procurement Platform

企业采购与供应链智能协同平台，采用模块化单体架构，由两名成员按业务域纵向协作开发。

当前仓库阶段：工程治理、数据库底座、身份认证、IAM/RBAC、组织树、采购主数据和
Member A 主线已完成：采购申请、顺序审批、采购订单、收货检验、inventory-lite、
发票三单匹配和正式审计闭环均已实现。寻源、RAG、Agent 及异步事件投递仍属于
Member B 后续交付范围。

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
采购申请状态、权限、金额和主数据引用规则见
[procurement requests](docs/architecture/procurement-requests.md)。
审批模板、实例、节点、操作历史和采购状态联动见
[approval workflow](docs/architecture/approval-workflow.md)。
采购订单的拆单数量控制、供应商门禁、金额和状态规则见
[purchase orders](docs/architecture/purchase-orders.md)。
收货草稿、检验、合格数量入账和订单状态联动见
[goods receiving](docs/architecture/goods-receiving.md)。
供应商发票、数量/价格匹配、异常审批和订单关闭规则见
[invoice matching](docs/architecture/invoice-matching.md)。
验收合格入库、库存流水和正式业务审计规则见
[inventory and audit](docs/architecture/inventory-audit.md)。

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
