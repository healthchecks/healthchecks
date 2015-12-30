from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from hc.api.models import Check


class Command(BaseCommand):
    help = 'Prune anonymous checks older than 2 hours'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=2)
        Check.objects.filter(user=None, created__lt=cutoff).delete()
