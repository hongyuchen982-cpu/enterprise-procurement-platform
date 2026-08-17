# Frozen architecture

The platform is a modular monolith. FastAPI exposes APIs; application services own use-case orchestration and transactions; domain rules enforce state transitions; repositories and SQLAlchemy persist formal business state to MySQL.

Infrastructure responsibilities are frozen:

- MySQL: formal business data and control-state source of truth.
- Redis: cache, short locks, rate limiting, and temporary state.
- RabbitMQ: asynchronous message transport.
- MinIO: original binary files.
- Qdrant: rebuildable vector retrieval projection.

Cross-module synchronous calls use provider-owned facades and contract DTOs. Asynchronous facts use transactional outbox, RabbitMQ, worker, and consumer inbox. Agents can only invoke provider-owned tool handlers through the Tool Registry, permission/data-scope checks, risk gate, and confirmation boundary.

The repository must not introduce microservices, Kubernetes, Kafka, service mesh, event sourcing, CQRS, or Elasticsearch during the current phase.
