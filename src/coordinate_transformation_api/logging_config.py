import logging
from datetime import UTC, datetime
from typing import Any

from pythonjsonlogger import json as jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""

    def __init__(self: "CustomJsonFormatter", *args: object, use_colors: bool = False, **kwargs: object) -> None:  # noqa: ARG002
        """Initialize formatter, ignoring use_colors parameter added by uvicorn."""
        # Remove use_colors from kwargs if present, as pythonjsonlogger doesn't support it
        kwargs.pop("use_colors", None)
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    def add_fields(
        self: "CustomJsonFormatter", log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        # Add timestamp with ISO format
        log_record["timestamp"] = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        log_record["logger"] = record.name
        log_record["level"] = record.levelname
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Remove color-related fields added by uvicorn
        log_record.pop("color_message", None)


class AccessLogFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for access logs with client IP and optional X-Forwarded-For."""

    def __init__(
        self: "AccessLogFormatter",
        *args: object,
        log_forwarded_for: bool = False,
        client_ip_header: str | None = None,
        use_colors: bool = False,  # noqa: ARG002
        **kwargs: object,
    ) -> None:
        """Initialize formatter, ignoring use_colors parameter added by uvicorn."""
        # Remove use_colors from kwargs if present, as pythonjsonlogger doesn't support it
        kwargs.pop("use_colors", None)
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.log_forwarded_for = log_forwarded_for
        self.client_ip_header = client_ip_header

    def add_fields(
        self: "AccessLogFormatter", log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        # Add timestamp with ISO format
        log_record["timestamp"] = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        log_record["logger"] = record.name
        log_record["level"] = record.levelname

        # Parse uvicorn access log message to extract components
        # Format: '{client_addr} - "{method} {path} {http_version}" {status_code}'
        if hasattr(record, "args") and record.args:
            try:
                # Uvicorn access logs pass these as args tuple
                args = tuple(record.args) if not isinstance(record.args, tuple) else record.args
                min_args_count = 5
                if len(args) >= min_args_count:
                    client_addr = str(args[0])
                    # Extract IP from "ip:port" format
                    log_record["client_ip"] = client_addr.split(":")[0] if ":" in client_addr else client_addr
                    log_record["method"] = args[1]
                    log_record["path"] = args[2]
                    log_record["http_version"] = args[3]
                    log_record["status_code"] = args[4]
            except (IndexError, AttributeError, TypeError):
                pass

        # Add X-Forwarded-For if configured and available
        if self.log_forwarded_for and hasattr(record, "x_forwarded_for"):
            x_forwarded_for = record.x_forwarded_for
            log_record["x_forwarded_for"] = x_forwarded_for
            # Extract real client IP (first IP in X-Forwarded-For chain)
            # Format: "client, proxy1, proxy2, ..."
            first_ip = x_forwarded_for.split(",")[0].strip()
            if first_ip:
                log_record["real_client_ip"] = first_ip

        # Add alternative client IP header if configured
        if self.client_ip_header and hasattr(record, "client_ip_value"):
            client_ip_value = record.client_ip_value
            log_record[self.client_ip_header.lower().replace("-", "_")] = client_ip_value
            # Use this as the real client IP
            log_record["real_client_ip"] = client_ip_value.strip()

        # Add Host header if available
        if hasattr(record, "host"):
            log_record["host"] = record.host

        # Add response time if available (in milliseconds)
        if hasattr(record, "response_time"):
            log_record["response_time_ms"] = record.response_time

        # Remove color-related fields added by uvicorn
        log_record.pop("color_message", None)


def get_json_logging_config(
    log_level: str,
    access_log_enabled: bool = False,
    log_forwarded_for: bool = False,
    client_ip_header: str | None = None,
) -> dict[str, Any]:
    """
    Get uvicorn logging configuration with JSON formatting.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        access_log_enabled: Whether to enable access logs
        log_forwarded_for: Whether to include X-Forwarded-For header in logs
        client_ip_header: Alternative header to extract real client IP

    Returns:
        Dictionary with logging configuration for uvicorn
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_metadata": {
                "()": "coordinate_transformation_api.access_log_middleware.RequestMetadataFilter",
                "log_forwarded_for": log_forwarded_for,
                "client_ip_header": client_ip_header,
            },
        },
        "formatters": {
            "default": {
                "()": "coordinate_transformation_api.logging_config.CustomJsonFormatter",
            },
            "json": {
                "()": "coordinate_transformation_api.logging_config.CustomJsonFormatter",
            },
            "access": {
                "()": "coordinate_transformation_api.logging_config.AccessLogFormatter",
                "log_forwarded_for": log_forwarded_for,
                "client_ip_header": client_ip_header,
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
            "access_console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "access",
                "stream": "ext://sys.stdout",
                "filters": ["request_metadata"],
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access_console"],
                "level": log_level if access_log_enabled else "CRITICAL",
                "propagate": False,
            },
            "coordinate_transformation_api": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["default"],
        },
    }
