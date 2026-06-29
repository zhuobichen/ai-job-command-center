"""Structured logging configuration for job_hunt.

Provides JSON logging for production and human-readable format for development.
"""

import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    JSON = "json"
    CONSOLE = "console"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_type: LogFormat = LogFormat.CONSOLE,
    project_root: Optional[Path] = None,
) -> logging.Logger:
    """Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        format_type: Output format (json for production, console for dev)
        project_root: Project root directory for relative paths

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("job_hunt")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    log_format = _JSONLogFormatter() if format_type == LogFormat.JSON else _ConsoleLogFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        if not log_path.is_absolute() and project_root:
            log_path = project_root / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(_JSONLogFormatter())
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    return logger


class _JSONLogFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data, ensure_ascii=False)


class _ConsoleLogFormatter(logging.Formatter):
    """Colored console formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        reset = self.RESET

        if record.levelname == "INFO":
            prefix = f"{color}[INFO]{reset}"
        elif record.levelname == "WARNING":
            prefix = f"{color}[WARN]{reset}"
        elif record.levelname == "ERROR":
            prefix = f"{color}[ERROR]{reset}"
        elif record.levelname == "DEBUG":
            prefix = f"{color}[DEBUG]{reset}"
        else:
            prefix = f"{color}[{record.levelname}]{reset}"

        return f"{prefix} {record.getMessage()}"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name. If None, returns root job_hunt logger.

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"job_hunt.{name}")
    return logging.getLogger("job_hunt")


class LogContext:
    """Context manager for adding extra fields to log records."""

    def __init__(self, logger: logging.Logger, **kwargs):
        self.logger = logger
        self.extra = kwargs
        self._old_factory = None

    def __enter__(self):
        self._old_factory = logging.getLogRecordFactory()

        def _record_factory(*args, **kwargs):
            record = self._old_factory(*args, **kwargs)
            record.extra = self.extra
            return record

        logging.setLogRecordFactory(_record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self._old_factory)
        return False


# Default logger instance
default_logger = get_logger()
