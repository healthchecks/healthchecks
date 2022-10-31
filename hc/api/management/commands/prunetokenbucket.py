from __future__ import annotations

from datetime import timedelta as td

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from hc.api.models import TokenBucket


class Command(BaseCommand):
    help = "Prune pings based on limits in user profiles"

    def handle(self, *args, **options):

        day_ago = now() - td(days=1)
        q = TokenBucket.objects.filter(updated__lt=day_ago)
        n_pruned, _ = q.delete()

        return "Done! Pruned %d token bucket entries" % n_pruned
