from functools import lru_cache
from urllib.parse import quote, quote_plus

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BusinessSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "procurement"
    mysql_user: str = "procurement"
    mysql_password: SecretStr = SecretStr("change-me-local-only")
    database_url_override: str | None = Field(
        default=None, validation_alias="DATABASE_URL", repr=False
    )
    auth_session_ttl_minutes: int = Field(default=480, ge=5, le=10080)
    auth_max_failed_attempts: int = Field(default=5, ge=3, le=20)
    auth_lockout_minutes: int = Field(default=15, ge=1, le=1440)

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: SecretStr = SecretStr("change-redis-me-local-only")

    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "procurement"
    rabbitmq_password: SecretStr = SecretStr("change-rabbit-me-local-only")
    rabbitmq_vhost: str = "procurement"

    minio_host: str = "localhost"
    minio_api_port: int = 9000
    minio_root_user: str = "procurement-minio"
    minio_root_password: SecretStr = SecretStr("change-minio-me-local-only")
    minio_bucket: str = "procurement-files"
    minio_secure: bool = False

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        password = quote_plus(self.mysql_password.get_secret_value())
        return (
            f"mysql+pymysql://{self.mysql_user}:{password}@{self.mysql_host}:"
            f"{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        password = quote(self.redis_password.get_secret_value(), safe="")
        return f"redis://:{password}@{self.redis_host}:{self.redis_port}/0"

    @property
    def rabbitmq_url(self) -> str:
        user = quote(self.rabbitmq_user, safe="")
        password = quote(self.rabbitmq_password.get_secret_value(), safe="")
        vhost = quote(self.rabbitmq_vhost, safe="")
        return f"amqp://{user}:{password}@{self.rabbitmq_host}:{self.rabbitmq_port}/{vhost}"

    @property
    def minio_endpoint(self) -> str:
        return f"{self.minio_host}:{self.minio_api_port}"


@lru_cache
def get_business_settings() -> BusinessSettings:
    return BusinessSettings()
