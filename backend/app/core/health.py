import asyncio
from typing import Literal

import aio_pika
import redis
from minio import Minio
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sqlalchemy import text

from app.core.database import engine
from app.core.settings.ai import get_ai_settings
from app.core.settings.business import get_business_settings


class DependencyStatus(BaseModel):
    status: Literal["up", "down"]
    detail: str | None = None


class ReadinessResult(BaseModel):
    status: Literal["ready", "degraded", "not_ready"]
    dependencies: dict[str, DependencyStatus]


def _up() -> DependencyStatus:
    return DependencyStatus(status="up")


def _down(error: Exception) -> DependencyStatus:
    return DependencyStatus(status="down", detail=error.__class__.__name__)


def _check_mysql() -> DependencyStatus:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return _up()
    except Exception as error:  # pragma: no cover - exercised against live infrastructure
        return _down(error)


def _check_redis() -> DependencyStatus:
    settings = get_business_settings()
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        client.close()
        return _up()
    except Exception as error:  # pragma: no cover - exercised against live infrastructure
        return _down(error)


def _check_minio() -> DependencyStatus:
    settings = get_business_settings()
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
        client.list_buckets()
        return _up()
    except Exception as error:  # pragma: no cover - exercised against live infrastructure
        return _down(error)


def _check_qdrant() -> DependencyStatus:
    settings = get_ai_settings()
    try:
        client = QdrantClient(url=settings.qdrant_url, timeout=2)
        client.get_collections()
        client.close()
        return _up()
    except Exception as error:  # pragma: no cover - exercised against live infrastructure
        return _down(error)


async def _check_rabbitmq() -> DependencyStatus:
    settings = get_business_settings()
    connection: aio_pika.abc.AbstractRobustConnection | None = None
    try:
        connection = await asyncio.wait_for(
            aio_pika.connect_robust(settings.rabbitmq_url), timeout=3
        )
        return _up()
    except Exception as error:  # pragma: no cover - exercised against live infrastructure
        return _down(error)
    finally:
        if connection is not None:
            await connection.close()


async def check_readiness() -> ReadinessResult:
    mysql, redis_status, rabbitmq, minio, qdrant = await asyncio.gather(
        asyncio.to_thread(_check_mysql),
        asyncio.to_thread(_check_redis),
        _check_rabbitmq(),
        asyncio.to_thread(_check_minio),
        asyncio.to_thread(_check_qdrant),
    )
    dependencies = {
        "mysql": mysql,
        "redis": redis_status,
        "rabbitmq": rabbitmq,
        "minio": minio,
        "qdrant": qdrant,
    }
    if mysql.status == "down":
        overall: Literal["ready", "degraded", "not_ready"] = "not_ready"
    elif any(item.status == "down" for item in dependencies.values()):
        overall = "degraded"
    else:
        overall = "ready"
    return ReadinessResult(status=overall, dependencies=dependencies)
