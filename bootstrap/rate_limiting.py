"""Rate limiter oparty na cache (Redis).

Chroni najcięższe endpointy API przed atakami wolumetrycznymi (AUDYT-095).
"""

import time
from collections.abc import Callable
from typing import Any

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.utils.functional import cached_property


def _get_client_ip(request: HttpRequest) -> str:
    """Extracts client IP from request, respecting X-Forwarded-For."""
    forwarded: str | None = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return str(request.META.get("REMOTE_ADDR", "unknown"))  # type: ignore[no-any-return]


def _rate_limit_key(scope: str, identifier: str, window: int) -> str:
    """Generates a cache key that includes window for automatic expiry."""
    epoch_minute = int(time.time()) // window
    return f"ratelimit:{scope}:{identifier}:{epoch_minute}"


def check_rate_limit(
    scope: str,
    request: HttpRequest,
    limit: int,
    window: int,
) -> bool:
    """Checks if request is within rate limit.

    Returns True if request is allowed, False if rate limited.
    """
    identifier = _get_client_ip(request)
    if getattr(request, "user", None) and getattr(request.user, "is_authenticated", False):
        identifier = f"user:{request.user.id}"
    key = _rate_limit_key(scope, identifier, window)

    current = cache.get(key)
    if current is None:
        cache.set(key, 1, timeout=window)
        return True

    if current >= limit:
        return False

    cache.incr(key)
    return True


def rate_limited_response(request: HttpRequest, window: int = 60) -> JsonResponse:
    """Buduje odpowiedź 429 Too Many Requests (RFC 7807)."""
    return JsonResponse(
        {
            "type": "https://api.pttk-badges.pl/errors/rate-limit",
            "title": "Rate Limit Exceeded",
            "status": 429,
            "detail": "Zbyt duża liczba zapytań. Spróbuj ponownie później.",
            "retry_after": window,
            "instance": request.path,
            "request_id": getattr(request, "request_id", "unknown"),
        },
        status=429,
        headers={"Retry-After": str(window)},
    )


def rate_limit(limit: int, window: int = 60) -> Callable[..., Any]:
    """Decorator for rate limiting view methods.

    Args:
        limit: max requests in window.
        window: time window in seconds (default 60s).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: object, request: HttpRequest, *args: object, **kwargs: object) -> Any:
            if not check_rate_limit(func.__name__, request, limit, window):
                return rate_limited_response(request, window)
            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


class RateLimited:
    """Mixin providing rate-limited dispatch for Django Views.

    Usage:
        class MyView(RateLimited, View):
            rate_limit = (100, 60)  # 100 requests per 60s
            ...
    """

    rate_limit: tuple[int, int] = (100, 60)

    @cached_property
    def _rate_limit_limit(self) -> int:
        return self.rate_limit[0]

    @cached_property
    def _rate_limit_window(self) -> int:
        return self.rate_limit[1]

    def _check_rate_limit(self, request: HttpRequest) -> bool:
        """Check rate limit for current view class."""
        limit, window = self._rate_limit_limit, self._rate_limit_window
        return check_rate_limit(self.__class__.__name__, request, limit, window)
