from __future__ import annotations

from typing import Any

from django.conf import settings
from django.test.runner import DiscoverRunner


class CustomRunner(DiscoverRunner):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # For speed:
        settings.PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

        # Send emails synchronously
        settings.BLOCKING_EMAILS = True
        # Make sure EMAIL_HOST is set as hc.lib.emails.send() requires it
        settings.EMAIL_HOST = "example.org"

        super(CustomRunner, self).__init__(*args, **kwargs)
