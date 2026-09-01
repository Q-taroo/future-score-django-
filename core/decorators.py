from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """Server-side authorization gate for every admin view (spec §23).
    Never trust a client-side role check alone — this decorator re-checks
    request.user.role on every request."""

    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied("権限がありません")
        return view_func(request, *args, **kwargs)

    return wrapped
