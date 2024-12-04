from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.http.response import HttpResponse
from django.urls import reverse


def absolute_url(path: str) -> str:
    subpath = urlparse(settings.SITE_ROOT).path
    return settings.SITE_ROOT.removesuffix(subpath) + path


def absolute_reverse(
    viewname: str | Callable[..., HttpResponse], args: Sequence[Any] | None = None
) -> str:
    """Generate absolute URL (starting with http[s]://)."""
    return absolute_url(reverse(viewname, args=args))
