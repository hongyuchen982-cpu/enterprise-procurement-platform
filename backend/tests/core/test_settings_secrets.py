from app.core.settings.base import BaseAppSettings
from app.core.settings.business import BusinessSettings


def test_sensitive_settings_are_masked_in_representations() -> None:
    business = BusinessSettings(
        _env_file=None,
        mysql_password="mysql-sensitive-value",
        redis_password="redis-sensitive-value",
        rabbitmq_password="rabbit-sensitive-value",
        minio_root_password="minio-sensitive-value",
    )
    base = BaseAppSettings(_env_file=None, secret_key="application-sensitive-value")

    combined_repr = repr(business) + repr(base)
    assert "mysql-sensitive-value" not in combined_repr
    assert "redis-sensitive-value" not in combined_repr
    assert "rabbit-sensitive-value" not in combined_repr
    assert "minio-sensitive-value" not in combined_repr
    assert "application-sensitive-value" not in combined_repr
