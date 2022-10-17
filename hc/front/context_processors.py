from __future__ import annotations

from django.conf import settings


def branding(request):
    return {
        "site_name": settings.SITE_NAME,
        "site_logo_url": settings.SITE_LOGO_URL,
    }
