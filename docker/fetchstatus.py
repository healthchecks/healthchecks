from __future__ import annotations

from typing import Any
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, **options: Any) -> str:
        host = settings.ALLOWED_HOSTS[0]
        if host == "*":
            host = "localhost"

        req = Request("http://localhost:8000/api/v3/status/", headers={"Host": host})
        with urlopen(req) as response:
            assert response.status == 200

        return "Status OK"
