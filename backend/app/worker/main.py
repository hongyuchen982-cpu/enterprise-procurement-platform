from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aio_pika
import uvicorn
from fastapi import FastAPI, Response, status

from app.core.logging import configure_logging
from app.core.settings.base import get_base_settings
from app.core.settings.business import get_business_settings
from app.worker.health import WorkerHealth


@asynccontextmanager
async def worker_lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_business_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    app.state.rabbitmq_connection = connection
    try:
        yield
    finally:
        await connection.close()


worker_app = FastAPI(title="Enterprise Procurement Worker", lifespan=worker_lifespan)


@worker_app.get("/health", response_model=WorkerHealth)
async def health(response: Response) -> WorkerHealth:
    connection = getattr(worker_app.state, "rabbitmq_connection", None)
    if connection is None or connection.is_closed:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return WorkerHealth(status="not_ready", rabbitmq="down")
    return WorkerHealth(status="ready", rabbitmq="up")


def run() -> None:
    settings = get_base_settings()
    uvicorn.run(worker_app, host="0.0.0.0", port=settings.worker_health_port)


if __name__ == "__main__":
    run()
