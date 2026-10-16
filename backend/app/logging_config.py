import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "service.name": "equipment-api",
        }

        for field in (
            "request_id",
            "method",
            "route",
            "status",
            "duration_ms",
        ):
            if hasattr(record, field):
                event[field] = getattr(record, field)

        return json.dumps(event, ensure_ascii=False)


def build_log_config(level: str) -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "app.logging_config.JsonFormatter",
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json",
            }
        },
        "root": {
            "level": level.upper(),
            "handlers": ["stdout"],
        },
        "loggers": {
            "uvicorn": {
                "handlers": [],
                "level": level.upper(),
                "propagate": True,
            },
            "uvicorn.error": {
                "handlers": [],
                "level": level.upper(),
                "propagate": True,
            },
            "uvicorn.access": {
                "handlers": [],
                "level": level.upper(),
                "propagate": True,
            },
        },
    }
