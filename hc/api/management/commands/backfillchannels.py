from django.core.management.base import BaseCommand

from hc.api.models import Channel, Notification


class Command(BaseCommand):
    help = "Backfill Channel.last_notify and Channel.last_error"

    def handle(self, *args, **options):
        total = 0

        for channel in Channel.objects.all():
            q = Channel.objects.filter(id=channel.id)

            try:
                n = Notification.objects.filter(channel=channel).latest()
                q.update(last_notify=n.created, last_error=n.error)
                total += 1
            except Notification.DoesNotExist:
                if channel.last_error:
                    q.update(last_error="")
                    total += 1

        return "Done! Updated %d channels." % total
