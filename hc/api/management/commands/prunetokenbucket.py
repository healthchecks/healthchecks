from __future__ import annotations

from datetime import timedelta as td
from typing import Any

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from hc.api.models import TokenBucket


class Command(BaseCommand):
    help = "Prune pings based on limits in user profiles"

    def handle(self, **options: Any) -> str:
        day_ago = now() - td(days=1)
        q = TokenBucket.objects.filter(updated__lt=day_ago)
        n_pruned, _ = q.delete()

        return f"Done! Pruned {n_pruned} token bucket entries"
