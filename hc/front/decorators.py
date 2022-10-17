from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.http import HttpResponse


def require_setting(key):
    def decorator(f):
        @wraps(f)
        def wrapper(request, *args, **kwds):
            if not getattr(settings, key):
                return HttpResponse(status=404)

            return f(request, *args, **kwds)

        return wrapper

    return decorator
