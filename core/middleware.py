from django.http import JsonResponse

from core.rate_limit import check_rate_limit, client_ip

# path-prefix -> (limit, window_seconds). Kept intentionally small: only
# the endpoints that are cheap to abuse (auth, voting) are throttled.
RATE_LIMITED_PATHS = {
    "/accounts/register/": (5, 60),
    "/accounts/login/": (10, 60),
    "/accounts/resend-verification/": (3, 900),
}
RATE_LIMITED_PREFIXES = {
    "/predictions/vote/": (30, 60),
}


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST":
            limit_window = RATE_LIMITED_PATHS.get(request.path)
            if limit_window is None:
                for prefix, lw in RATE_LIMITED_PREFIXES.items():
                    if request.path.startswith(prefix):
                        limit_window = lw
                        break
            if limit_window is not None:
                limit, window = limit_window
                identity = request.user.pk if request.user.is_authenticated else client_ip(request)
                key = f"{request.path}:{identity}"
                if not check_rate_limit(key, limit, window):
                    return JsonResponse(
                        {"error": {"code": "RATE_LIMITED", "message": "リクエストが多すぎます。しばらくしてから再度お試しください。"}},
                        status=429,
                    )
        return self.get_response(request)
