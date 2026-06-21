from __future__ import annotations

import logging
from logging.config import dictConfig
from typing import Any

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: str = "INFO") -> None:
    normalized_level = level.upper()
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": DEFAULT_LOG_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": normalized_level,
        },
    }
    dictConfig(config)
    logging.getLogger("jav_metadatahub").setLevel(normalized_level)
