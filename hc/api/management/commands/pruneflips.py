from django.core.management.base import BaseCommand

from hc.api.models import Flip
from hc.lib.date import month_boundaries


class Command(BaseCommand):
    help = "Prune old Flip objects."

    def handle(self, *args, **options):
        threshold = min(month_boundaries(months=3))

        q = Flip.objects.filter(created__lt=threshold)
        n_pruned, _ = q.delete()

        return "Done! Pruned %d flips." % n_pruned
