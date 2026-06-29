"""Environment validation and startup checks for job_hunt."""

import os
import sys
from pathlib import Path
from typing import NamedTuple, Optional

from .exceptions import ConfigurationError, MissingAPIKeyError
from .logging_config import get_logger

logger = get_logger("env")


class ValidationResult(NamedTuple):
    """Result of environment validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    info: dict[str, str]


class EnvironmentValidator:
    """Validates environment and configuration at startup."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: dict[str, str] = {}

    def validate_all(self) -> ValidationResult:
        """Run all validation checks.

        Returns:
            ValidationResult with validation status and any issues found
        """
        self.errors.clear()
        self.warnings.clear()
        self.info.clear()

        self._check_python_version()
        self._check_directory_structure()
        self._check_api_key()
        self._check_optional_dependencies()
        self._check_platform_tools()

        return ValidationResult(
            valid=len(self.errors) == 0,
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            info=self.info.copy(),
        )

    def _check_python_version(self):
        """Check Python version is >= 3.11."""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 11):
            self.errors.append(f"Python 3.11+ required, found {version.major}.{version.minor}")
        else:
            self.info["python"] = f"{version.major}.{version.minor}.{version.micro}"

    def _check_directory_structure(self):
        """Check required directories exist or can be created."""
        required_dirs = ["data", "output", "logs"]

        for dirname in required_dirs:
            path = self.project_root / dirname
            if path.exists():
                self.info[dirname] = str(path)
            else:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    self.warnings.append(f"Created missing directory: {dirname}")
                    self.info[dirname] = str(path)
                except OSError as e:
                    self.errors.append(f"Cannot create directory {dirname}: {e}")

    def _check_api_key(self):
        """Check API key is configured."""
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")

        # Also check config file
        config_path = self.project_root / "config.toml"
        config_key = ""
        if config_path.exists():
            try:
                import tomllib
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                    config_key = config.get("ai", {}).get("api_key", "")
            except Exception:
                pass

        if api_key:
            self.info["api_key"] = "configured (env)"
        elif config_key:
            self.info["api_key"] = "configured (config)"
        else:
            self.warnings.append(
                "No API key configured. Some features will be unavailable. "
                "Set DEEPSEEK_API_KEY environment variable or add to config.toml"
            )

    def _check_optional_dependencies(self):
        """Check optional dependencies are available."""
        optional_deps = {
            "playwright": "browser",
            "weasyprint": "pdf",
            "python-docx": "docx",
        }

        for module, feature in optional_deps.items():
            try:
                __import__(module)
                self.info[feature] = "available"
            except ImportError:
                self.warnings.append(f"{feature} features require: pip install job-hunt[{feature}]")

    def _check_platform_tools(self):
        """Check external platform tools."""
        import shutil

        if shutil.which("browser-act"):
            self.info["browser-act"] = "available"
        else:
            self.warnings.append(
                "browser-act not found. Some scraping features may be limited. "
                "Install with: uv tool install browser-act-cli --python 3.12"
            )

    def raise_if_invalid(self):
        """Raise ConfigurationError if validation failed."""
        result = self.validate_all()
        if not result.valid:
            error_msg = "\n".join(result.errors)
            raise ConfigurationError(f"Environment validation failed:\n{error_msg}")


def validate_environment(project_root: Optional[Path] = None) -> ValidationResult:
    """Validate the environment and return results.

    Args:
        project_root: Project root directory

    Returns:
        ValidationResult with validation status
    """
    validator = EnvironmentValidator(project_root)
    return validator.validate_all()


def require_api_key() -> str:
    """Ensure API key is available, raise error if not.

    Returns:
        The API key string

    Raises:
        MissingAPIKeyError: If no API key is configured
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    if not api_key:
        # Try config file
        config_path = Path.cwd() / "config.toml"
        if config_path.exists():
            try:
                import tomllib
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                    api_key = config.get("ai", {}).get("api_key", "")
            except Exception:
                pass

    if not api_key:
        raise MissingAPIKeyError()

    return api_key


def check_startup(project_root: Optional[Path] = None) -> bool:
    """Run startup checks and log results.

    Args:
        project_root: Project root directory

    Returns:
        True if startup checks passed
    """
    result = validate_environment(project_root)

    if result.errors:
        for error in result.errors:
            logger.error(f"Startup error: {error}")
        return False

    if result.warnings:
        for warning in result.warnings:
            logger.warning(warning)

    for key, value in result.info.items():
        logger.info(f"{key}: {value}")

    return True
