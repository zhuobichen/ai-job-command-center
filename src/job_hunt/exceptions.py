"""Custom exception classes for job_hunt."""


class JobHuntError(Exception):
    """Base exception for all job_hunt errors."""

    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or "JOB_HUNT_ERROR"
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details,
        }


# ─── Configuration Errors ──────────────────────────────────

class ConfigurationError(JobHuntError):
    """Configuration related errors."""
    code = "CONFIG_ERROR"


class MissingAPIKeyError(ConfigurationError):
    """API key is missing or not configured."""
    code = "MISSING_API_KEY"

    def __init__(self, provider: str = "deepseek"):
        super().__init__(
            f"API key for {provider} is not configured. Set DEEPSEEK_API_KEY environment variable or configure in config.toml.",
            code="MISSING_API_KEY",
            details={"provider": provider},
        )


class InvalidConfigError(ConfigurationError):
    """Invalid configuration value."""
    code = "INVALID_CONFIG"


# ─── Database Errors ──────────────────────────────────────

class DatabaseError(JobHuntError):
    """Database related errors."""
    code = "DATABASE_ERROR"


class DatabaseConnectionError(DatabaseError):
    """Cannot connect to database."""
    code = "DB_CONNECTION_ERROR"


class RecordNotFoundError(DatabaseError):
    """Requested record not found."""
    code = "RECORD_NOT_FOUND"

    def __init__(self, record_type: str, record_id: int | str):
        super().__init__(
            f"{record_type} with id={record_id} not found",
            code="RECORD_NOT_FOUND",
            details={"record_type": record_type, "record_id": record_id},
        )


# ─── Scraper Errors ───────────────────────────────────────

class ScraperError(JobHuntError):
    """Base exception for scraper errors."""
    code = "SCRAPER_ERROR"


class PlatformUnavailableError(ScraperError):
    """The job platform is unavailable."""
    code = "PLATFORM_UNAVAILABLE"

    def __init__(self, platform: str, reason: str = ""):
        super().__init__(
            f"Platform {platform} is unavailable" + (f": {reason}" if reason else ""),
            code="PLATFORM_UNAVAILABLE",
            details={"platform": platform, "reason": reason},
        )


class ScrapingTimeoutError(ScraperError):
    """Scraping operation timed out."""
    code = "SCRAPING_TIMEOUT"

    def __init__(self, platform: str, timeout_seconds: int):
        super().__init__(
            f"Scraping {platform} timed out after {timeout_seconds}s",
            code="SCRAPING_TIMEOUT",
            details={"platform": platform, "timeout_seconds": timeout_seconds},
        )


class AntiBotDetectedError(ScraperError):
    """Anti-bot or rate limiting detected."""
    code = "ANTI_BOT_DETECTED"

    def __init__(self, platform: str):
        super().__init__(
            f"Anti-bot detection on {platform}. Consider reducing request frequency.",
            code="ANTI_BOT_DETECTED",
            details={"platform": platform},
        )


# ─── AI/LLM Errors ─────────────────────────────────────────

class AIError(JobHuntError):
    """AI/LLM related errors."""
    code = "AI_ERROR"


class AIResponseError(AIError):
    """AI returned an invalid or unexpected response."""
    code = "AI_RESPONSE_ERROR"


class AIQuotaExceededError(AIError):
    """AI API quota exceeded."""
    code = "AI_QUOTA_EXCEEDED"


# ─── Validation Errors ─────────────────────────────────────

class ValidationError(JobHuntError):
    """Input validation failed."""
    code = "VALIDATION_ERROR"


class InvalidResumeError(ValidationError):
    """Resume data is invalid or incomplete."""
    code = "INVALID_RESUME"


class InvalidJobError(ValidationError):
    """Job data is invalid."""
    code = "INVALID_JOB"


# ─── Application Errors ───────────────────────────────────

class ApplicationError(JobHuntError):
    """Job application related errors."""
    code = "APPLICATION_ERROR"


class ApplicationThresholdError(ApplicationError):
    """Job score below threshold for application."""
    code = "THRESHOLD_NOT_MET"

    def __init__(self, job_id: int, score: float, threshold: float):
        super().__init__(
            f"Job #{job_id} score {score:.1f} is below threshold {threshold}",
            code="THRESHOLD_NOT_MET",
            details={"job_id": job_id, "score": score, "threshold": threshold},
        )


class BlacklistedCompanyError(ApplicationError):
    """Company is on blacklist."""
    code = "COMPANY_BLACKLISTED"

    def __init__(self, company: str):
        super().__init__(
            f"Company '{company}' is on the blacklist",
            code="COMPANY_BLACKLISTED",
            details={"company": company},
        )
