from collections.abc import Sequence
from typing import Any
from django.conf import settings
from django.urls import reverse


def absolute_reverse(viewname: str, args: Sequence[Any] | None = None) -> str:
    return settings.SITE_ROOT + reverse(viewname, args=args)
