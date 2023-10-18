from __future__ import annotations

from datetime import timedelta as td
from typing import Any

from django.core.management.base import BaseCommand

from hc.api.models import Flip
from hc.lib.date import month_boundaries


class Command(BaseCommand):
    help = "Prune old Flip objects."

    def handle(self, **options: Any) -> str:
        threshold = min(month_boundaries(3, "UTC")) - td(days=1)

        q = Flip.objects.filter(created__lt=threshold)
        n_pruned, _ = q.delete()

        return f"Done! Pruned {n_pruned} flips."
