from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def payments(request: HttpRequest) -> dict[str, bool]:
    return {"show_pricing": settings.USE_PAYMENTS}
