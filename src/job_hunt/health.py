"""Health check utilities for job_hunt."""

import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .logging_config import get_logger
from .env_validator import validate_environment

logger = get_logger("health")


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    healthy: bool
    component: str
    status: str
    details: Optional[dict] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        result = {
            "healthy": self.healthy,
            "component": self.component,
            "status": self.status,
            "timestamp": self.timestamp,
        }
        if self.details:
            result["details"] = self.details
        return result


class HealthCheck:
    """Health check for the application and its dependencies."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self._start_time = time.time()

    def check_all(self) -> dict[str, HealthCheckResult]:
        """Run all health checks.

        Returns:
            Dictionary of component -> HealthCheckResult
        """
        results: dict[str, HealthCheckResult] = {}

        results["environment"] = self._check_environment()
        results["dependencies"] = self._check_dependencies()
        results["directories"] = self._check_directories()
        results["database"] = self._check_database()
        results["api_key"] = self._check_api_key()

        return results

    def is_healthy(self) -> bool:
        """Check if all critical components are healthy."""
        results = self.check_all()
        critical = ["environment", "dependencies", "directories", "api_key"]
        return all(
            results[c].healthy for c in critical
        )

    def get_status_summary(self) -> dict:
        """Get a summary of all health checks."""
        results = self.check_all()
        return {
            "healthy": self.is_healthy(),
            "uptime_seconds": time.time() - self._start_time,
            "checks": {name: result.to_dict() for name, result in results.items()},
        }

    def _check_environment(self) -> HealthCheckResult:
        """Check environment configuration."""
        try:
            validation = validate_environment(self.project_root)
            return HealthCheckResult(
                healthy=validation.valid,
                component="environment",
                status="ok" if validation.valid else "configuration_error",
                details={
                    "python_version": sys.version,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                },
            )
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                component="environment",
                status="error",
                details={"error": str(e)},
            )

    def _check_dependencies(self) -> HealthCheckResult:
        """Check required dependencies are importable."""
        required = ["typer", "rich", "httpx", "beautifulsoup4", "pydantic", "litellm"]
        missing = []

        for module in required:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)

        if missing:
            return HealthCheckResult(
                healthy=False,
                component="dependencies",
                status="missing_modules",
                details={"missing": missing},
            )

        return HealthCheckResult(
            healthy=True,
            component="dependencies",
            status="ok",
            details={"required": len(required), "all_present": True},
        )

    def _check_directories(self) -> HealthCheckResult:
        """Check required directories are accessible."""
        required_dirs = ["data", "output", "logs"]
        issues = []
        created = []

        for dirname in required_dirs:
            path = self.project_root / dirname
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    created.append(dirname)
                except OSError as e:
                    issues.append(f"{dirname}: {e}")
            elif not os.access(path, os.W_OK):
                issues.append(f"{dirname}: not writable")

        if issues:
            return HealthCheckResult(
                healthy=False,
                component="directories",
                status="access_error",
                details={"issues": issues},
            )

        return HealthCheckResult(
            healthy=True,
            component="directories",
            status="ok",
            details={"required": required_dirs, "created": created},
        )

    def _check_database(self) -> HealthCheckResult:
        """Check database connectivity."""
        db_path = self.project_root / "data" / "resume.db"

        if not db_path.exists():
            return HealthCheckResult(
                healthy=True,
                component="database",
                status="not_initialized",
                details={"db_path": str(db_path), "message": "Database will be created on first use"},
            )

        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM jobs")
            job_count = cursor.fetchone()[0]
            conn.close()

            return HealthCheckResult(
                healthy=True,
                component="database",
                status="ok",
                details={"db_path": str(db_path), "job_count": job_count},
            )
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                component="database",
                status="error",
                details={"db_path": str(db_path), "error": str(e)},
            )

    def _check_api_key(self) -> HealthCheckResult:
        """Check API key configuration."""
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")

        if not api_key:
            config_path = self.project_root / "config.toml"
            if config_path.exists():
                try:
                    import tomllib
                    with open(config_path, "rb") as f:
                        config = tomllib.load(f)
                        api_key = config.get("ai", {}).get("api_key", "")
                except Exception:
                    pass

        if api_key:
            masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
            return HealthCheckResult(
                healthy=True,
                component="api_key",
                status="configured",
                details={"api_key": masked},
            )

        return HealthCheckResult(
            healthy=True,
            component="api_key",
            status="not_configured",
            details={"message": "API key not set, some features will be unavailable"},
        )


def get_health_check(project_root: Optional[Path] = None) -> HealthCheck:
    """Get a health check instance.

    Args:
        project_root: Project root directory

    Returns:
        HealthCheck instance
    """
    return HealthCheck(project_root)


def quick_health_check() -> bool:
    """Quick health check returning boolean.

    Returns:
        True if healthy, False otherwise
    """
    try:
        return HealthCheck().is_healthy()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False
