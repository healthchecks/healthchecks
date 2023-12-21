from __future__ import annotations

import logging
from typing import Any

from django.core.management.base import BaseCommand

from hc.api.models import Check

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sequentially prune all checks in the database."

    def handle(self, **options: Any) -> str:
        for check in Check.objects.filter(n_pings__gt=100):
            print(f"Pruning: {check.code}")
            try:
                check.prune(wait=True)
            except Exception as e:
                logger.exception("Exception in Check.prune()")
        return "Done!"
