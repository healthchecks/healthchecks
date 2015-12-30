from django.core.management.base import BaseCommand
from hc.api.models import Check, Ping


class Command(BaseCommand):
    help = 'Fill check.n_pings field'

    def handle(self, *args, **options):
        for check in Check.objects.all():
            check.n_pings = Ping.objects.filter(owner=check).count()
            check.save(update_fields=("n_pings", ))

        return "Done!"
