"""AI智慧求职系统 - 纯CLI、本地运行、AI驱动、面向中国招聘市场"""

__version__ = "0.3.0"

# Core
from .cli import app
from .db.database import Database
from .utils.config import Config

# Exceptions
from .exceptions import (
    JobHuntError,
    ConfigurationError,
    MissingAPIKeyError,
    DatabaseError,
    ScraperError,
    AIError,
    ValidationError,
    ApplicationError,
)

# Utilities
from .logging_config import setup_logging, get_logger, LogContext
from .env_validator import validate_environment, check_startup, require_api_key
from .rate_limiter import RateLimiter, rate_limit, get_rate_limiter
from .health import HealthCheck, get_health_check, quick_health_check

__all__ = [
    # Version
    "__version__",
    # Core
    "app",
    "Config",
    "Database",
    # Exceptions
    "JobHuntError",
    "ConfigurationError",
    "MissingAPIKeyError",
    "DatabaseError",
    "ScraperError",
    "AIError",
    "ValidationError",
    "ApplicationError",
    # Utilities
    "setup_logging",
    "get_logger",
    "LogContext",
    "validate_environment",
    "check_startup",
    "require_api_key",
    "RateLimiter",
    "rate_limit",
    "get_rate_limiter",
    "HealthCheck",
    "get_health_check",
    "quick_health_check",
]
