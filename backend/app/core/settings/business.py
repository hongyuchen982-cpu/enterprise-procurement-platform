from functools import lru_cache
from urllib.parse import quote, quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class BusinessSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "procurement"
    mysql_user: str = "procurement"
    mysql_password: str = "change-me-local-only"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = "change-redis-me-local-only"

    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "procurement"
    rabbitmq_password: str = "change-rabbit-me-local-only"
    rabbitmq_vhost: str = "procurement"

    minio_host: str = "localhost"
    minio_api_port: int = 9000
    minio_root_user: str = "procurement-minio"
    minio_root_password: str = "change-minio-me-local-only"
    minio_bucket: str = "procurement-files"
    minio_secure: bool = False

    @property
    def database_url(self) -> str:
        password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{self.mysql_user}:{password}@{self.mysql_host}:"
            f"{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        password = quote(self.redis_password, safe="")
        return f"redis://:{password}@{self.redis_host}:{self.redis_port}/0"

    @property
    def rabbitmq_url(self) -> str:
        user = quote(self.rabbitmq_user, safe="")
        password = quote(self.rabbitmq_password, safe="")
        vhost = quote(self.rabbitmq_vhost, safe="")
        return f"amqp://{user}:{password}@{self.rabbitmq_host}:{self.rabbitmq_port}/{vhost}"

    @property
    def minio_endpoint(self) -> str:
        return f"{self.minio_host}:{self.minio_api_port}"


@lru_cache
def get_business_settings() -> BusinessSettings:
    return BusinessSettings()
