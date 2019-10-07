from django.db.models import F
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from hc.accounts.models import Profile
from hc.api.models import Ping


class Command(BaseCommand):
    help = "Prune pings based on limits in user profiles"

    def handle(self, *args, **options):
        # Create any missing user profiles
        for user in User.objects.filter(profile=None):
            Profile.objects.get_or_create(user_id=user.id)

        q = Ping.objects
        q = q.annotate(limit=F("owner__project__owner__profile__ping_log_limit"))
        q = q.filter(n__lte=F("owner__n_pings") - F("limit"))
        q = q.filter(n__gt=0)
        n_pruned, _ = q.delete()

        return "Done! Pruned %d pings" % n_pruned
