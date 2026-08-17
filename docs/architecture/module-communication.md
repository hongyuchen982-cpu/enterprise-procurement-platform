# Module communication

Use a facade when a caller needs an immediate authoritative result. Facades return contract DTOs and never ORM objects.

Use a domain event for a committed business fact whose consumers may run later. Cross-process delivery follows business transaction plus outbox, commit, outbox relay, RabbitMQ, worker, inbox deduplication, then consumer application service.

Use RabbitMQ only for durable asynchronous delivery, long-running jobs, external integrations, RAG indexing, and agent jobs. Do not use internal HTTP calls or RabbitMQ for synchronous in-process reads.

Agent business actions follow Agent Orchestrator, Tool Registry, permission/data-scope gate, risk gate, confirmation where required, provider-owned tool handler, business facade, application service, and repository. Agents must never import ORM models, repositories, or database sessions.
