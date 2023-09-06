from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from hc.lib.typealias import ViewFunc


def require_setting(key: str) -> Callable[[ViewFunc], ViewFunc]:
    def decorator(f: ViewFunc) -> ViewFunc:
        @wraps(f)
        def wrapper(request: HttpRequest, *args: Any, **kwds: Any) -> HttpResponse:
            if not getattr(settings, key):
                return HttpResponse(status=404)

            return f(request, *args, **kwds)

        return wrapper

    return decorator
