"""Minimal in-memory sliding-window rate limiter (spec §23).

Process-local by design: fine for a single-instance MVP deployment. Once
this runs on more than one server process/instance, swap the dict below
for Redis (e.g. django-redis) behind the same check_rate_limit()
signature — no caller needs to change.
"""

import time
import threading

_lock = threading.Lock()
_buckets: dict[str, tuple[int, float]] = {}  # key -> (count, reset_at)


def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    """Returns True if the call is allowed, False if the caller is over
    the limit for this key within the current window."""
    now = time.time()
    with _lock:
        count, reset_at = _buckets.get(key, (0, 0.0))
        if reset_at <= now:
            _buckets[key] = (1, now + window_seconds)
            return True
        if count >= limit:
            return False
        _buckets[key] = (count + 1, reset_at)
        return True


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
