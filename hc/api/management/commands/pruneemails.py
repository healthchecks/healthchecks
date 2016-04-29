from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from djmail.models import Message


class Command(BaseCommand):
    help = 'Prune stored email messages older than 7 days'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=7)
        n, _ = Message.objects.filter(sent_at__lt=cutoff).delete()
        return "Done! Pruned %d email messages." % n
