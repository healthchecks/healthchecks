from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from hc.api.models import Check

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sequentially prune all checks in the database."

    def handle(self, **options: Any) -> str:
        # Delete operations are sometimes slow, increase timeout
        settings.S3_TIMEOUT = 60

        for check in Check.objects.filter(n_pings__gt=100).order_by("code"):
            # Pruning of all checks is a potentially long operations, and some
            # checks may get removed while the operation is running.
            # To reduce the chance of hitting DoesNotExist exceptions,
            # before pruning each check make sure it still exists:
            if not Check.objects.filter(id=check.id).exists():
                continue

            print(f"Pruning: {check.code}")
            try:
                check.prune(wait=True)
            except Exception:
                logger.exception("Exception in Check.prune()")
        return "Done!"
