"""Rate limiting and anti-scraping utilities for job_hunt."""

import time
import threading
from typing import Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps

from .logging_config import get_logger

logger = get_logger("ratelimit")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 30
    requests_per_hour: int = 500
    requests_per_day: int = 3000
    burst_size: int = 5
    cooldown_seconds: int = 60


@dataclass
class RateLimitState:
    """Tracks rate limit state for a single source."""

    request_times: list[datetime] = field(default_factory=list)
    last_request_time: Optional[datetime] = None
    consecutive_failures: int = 0
    backoff_until: Optional[datetime] = None

    def add_request(self):
        """Record a new request."""
        now = datetime.now()
        self.request_times.append(now)
        self.last_request_time = now

    def is_in_backoff(self) -> bool:
        """Check if currently in backoff period."""
        if self.backoff_until is None:
            return False
        return datetime.now() < self.backoff_until

    def set_backoff(self, seconds: int):
        """Set backoff period after failure."""
        self.backoff_until = datetime.now() + timedelta(seconds=seconds)
        self.consecutive_failures += 1

    def clear_backoff(self):
        """Clear backoff after successful request."""
        self.backoff_until = None
        self.consecutive_failures = 0

    def get_backoff_duration(self) -> int:
        """Calculate backoff duration based on failures."""
        base = 60
        return min(base * (2 ** self.consecutive_failures), 3600)


class RateLimiter:
    """Token bucket rate limiter for controlling request frequency."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._states: dict[str, RateLimitState] = {}
        self._lock = threading.Lock()

    def get_state(self, source: str) -> RateLimitState:
        """Get or create state for a source."""
        with self._lock:
            if source not in self._states:
                self._states[source] = RateLimitState()
            return self._states[source]

    def can_proceed(self, source: str) -> tuple[bool, str]:
        """Check if a request can proceed.

        Returns:
            Tuple of (can_proceed, reason)
        """
        state = self.get_state(source)
        now = datetime.now()

        # Check backoff
        if state.is_in_backoff():
            remaining = (state.backoff_until - now).total_seconds()
            return False, f"Backoff until {state.backoff_until}, {remaining:.0f}s remaining"

        # Clean old requests
        self._clean_old_requests(state, now)

        # Check daily limit
        day_ago = now - timedelta(days=1)
        if len([t for t in state.request_times if t > day_ago]) >= self.config.requests_per_day:
            return False, f"Daily limit ({self.config.requests_per_day}) reached"

        # Check hourly limit
        hour_ago = now - timedelta(hours=1)
        if len([t for t in state.request_times if t > hour_ago]) >= self.config.requests_per_hour:
            return False, f"Hourly limit ({self.config.requests_per_hour}) reached"

        # Check minute limit
        minute_ago = now - timedelta(minutes=1)
        recent = [t for t in state.request_times if t > minute_ago]
        if len(recent) >= self.config.requests_per_minute:
            return False, f"Rate limit ({self.config.requests_per_minute}/min) reached"

        return True, "OK"

    def record_success(self, source: str):
        """Record a successful request."""
        state = self.get_state(source)
        state.add_request()
        state.clear_backoff()
        logger.debug(f"Request recorded for {source}")

    def record_failure(self, source: str):
        """Record a failed request and potentially trigger backoff."""
        state = self.get_state(source)
        state.set_backoff(state.get_backoff_duration())
        logger.warning(
            f"Request failed for {source}, backoff for {state.get_backoff_duration()}s "
            f"(consecutive failures: {state.consecutive_failures})"
        )

    def _clean_old_requests(self, state: RateLimitState, now: datetime):
        """Remove requests older than 24 hours."""
        day_ago = now - timedelta(days=1)
        state.request_times = [t for t in state.request_times if t > day_ago]


# Global rate limiter instance
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter


def set_rate_limiter(limiter: RateLimiter):
    """Set the global rate limiter instance."""
    global _global_limiter
    _global_limiter = limiter


def rate_limit(source: str, config: Optional[RateLimitConfig] = None):
    """Decorator for rate-limiting a function.

    Args:
        source: Name of the source/platform for rate limiting
        config: Optional rate limit configuration
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            if config:
                limiter = RateLimiter(config)

            can_proceed, reason = limiter.can_proceed(source)
            if not can_proceed:
                logger.warning(f"Rate limit reached for {source}: {reason}")
                raise RateLimitExceededError(source, reason)

            try:
                result = func(*args, **kwargs)
                limiter.record_success(source)
                return result
            except Exception as e:
                limiter.record_failure(source)
                raise

        return wrapper
    return decorator


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, source: str, reason: str):
        self.source = source
        self.reason = reason
        super().__init__(f"Rate limit exceeded for {source}: {reason}")


class AntiBotProtection:
    """Utilities for avoiding bot detection."""

    # Realistic user agents
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    @staticmethod
    def get_random_user_agent() -> str:
        """Get a random user agent string."""
        import random
        return random.choice(AntiBotProtection.USER_AGENTS)

    @staticmethod
    def get_request_headers(platform: str) -> dict:
        """Get headers that mimic a real browser.

        Args:
            platform: Target platform name

        Returns:
            Dictionary of HTTP headers
        """
        return {
            "User-Agent": AntiBotProtection.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    @staticmethod
    def should_wait(min_seconds: float = 1.0, max_seconds: float = 3.0) -> float:
        """Calculate random wait time to avoid detection.

        Returns:
            Seconds to wait
        """
        import random
        return random.uniform(min_seconds, max_seconds)


def wait_before_request(source: str, min_wait: float = 1.0, max_wait: float = 3.0):
    """Wait before making a request to avoid detection.

    Args:
        source: Platform name for rate limiting
        min_wait: Minimum seconds to wait
        max_wait: Maximum seconds to wait
    """
    wait_time = AntiBotProtection.should_wait(min_wait, max_wait)
    logger.debug(f"Waiting {wait_time:.2f}s before {source} request")
    time.sleep(wait_time)
