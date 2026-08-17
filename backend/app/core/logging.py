import logging

from app.core.settings.base import get_base_settings


def configure_logging() -> None:
    settings = get_base_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
