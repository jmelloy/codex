"""Logging configuration with colors and JSON support."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any
from contextvars import ContextVar

# ANSI color codes
COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[35m",  # Magenta
}
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

LIGHT_GRAY = "\033[37m"

class ColoredFormatter(logging.Formatter):
    """A formatter that adds colors to log output for terminal display."""

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        use_colors: bool = True,
    ):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # Save original values
        original_levelname = record.levelname
        original_name = record.name
        original_msg = record.msg

        if self.use_colors:
            color = COLORS.get(record.levelname, "")
            record.levelname = f"{color}{BOLD}{record.levelname:8}{RESET}"
            record.name = f"{DIM}{record.name}{RESET}"
            record.request_id = f"{LIGHT_GRAY}{getattr(record, 'request_id', '')}{RESET}"

        result = super().format(record)

        # Restore original values
        record.levelname = original_levelname
        record.name = original_name
        record.msg = original_msg
        record.request_id = getattr(record, "request_id", "")

        return result


class JSONFormatter(logging.Formatter):
    """A formatter that outputs logs as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
        }

        # Add location info
        if record.pathname:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        extra_keys = set(record.__dict__.keys()) - {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "taskName",
            "message",
        }
        for key in extra_keys:
            log_data[key] = getattr(record, key)

        return json.dumps(log_data, default=str)


class AccessFormatter(logging.Formatter):
    """Formatter for HTTP access logs with colors."""

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extract access log components if available
        client_addr = getattr(record, "client_addr", "-")
        request_line = getattr(record, "request_line", record.getMessage())
        status_code = getattr(record, "status_code", "-")

        if self.use_colors:
            # Color status codes
            status_str = str(status_code)
            if status_str.startswith("2"):
                status_colored = f"\033[32m{status_code}\033[0m"  # Green
            elif status_str.startswith("3"):
                status_colored = f"\033[36m{status_code}\033[0m"  # Cyan
            elif status_str.startswith("4"):
                status_colored = f"\033[33m{status_code}\033[0m"  # Yellow
            elif status_str.startswith("5"):
                status_colored = f"\033[31m{status_code}\033[0m"  # Red
            else:
                status_colored = str(status_code)

            return f'{timestamp} {DIM}{record.name}{RESET} {client_addr} "{request_line}" {status_colored} {getattr(record, "request_id", "")}'
        else:
            return f'{timestamp} {client_addr} "{request_line}" {status_code} {getattr(record, "request_id", "")}'


class RequestIdFilter(logging.Filter):
    """Logging filter that adds request ID from context variable."""
    def filter(self, record):
        from codex.main import request_id_var
        record.request_id = request_id_var.get()
        return True
    
def get_logging_config(
    log_level: str = "INFO",
    log_format: str = "colored",
    log_sql: bool = False,
) -> dict[str, Any]:
    """
    Generate logging configuration dictionary.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type - "colored" (default), "json", or "plain"
        log_sql: Whether to enable SQL query logging

    Returns:
        Dictionary suitable for logging.config.dictConfig()
    """
    use_colors = log_format == "colored"
    use_json = log_format == "json"

    if use_json:
        default_formatter = {
            "()": JSONFormatter,
        }
        access_formatter = {
            "()": JSONFormatter,
        }
    else:
        default_formatter = {
            "()": ColoredFormatter,
            "fmt": "%(asctime)s - %(levelname)6s %(name)s - %(message)s %(request_id)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
        access_formatter = {
            "()": AccessFormatter,
        }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": default_formatter,
            "access": access_formatter,
        },
        "filters": {
            "request_id": {
                "()": "codex.core.logging.RequestIdFilter",
            }
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "filters": ["request_id"],
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "filters": ["request_id"],
            },
        },
        "loggers": {
            "root": {
                "handlers": ["default"],
                "filters": ["request_id"],
            },
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO",
                "propagate": False,
            },
            "codex": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "INFO" if log_sql else "WARNING",
                "handlers": ["default"],
                "propagate": False,
            },
        },
    }
