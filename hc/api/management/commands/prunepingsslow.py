from django.db.models import F
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from hc.accounts.models import Profile
from hc.api.models import Check, Ping


class Command(BaseCommand):
    help = """Prune pings based on limits in user profiles.

    This command prunes each check individually. So it does the work
    in small chunks instead of a few big SQL queries like the `prunepings`
    command. It is appropriate for initial pruning of the potentially
    huge api_ping table.

    """

    def handle(self, *args, **options):
        # Create any missing user profiles
        for user in User.objects.filter(profile=None):
            Profile.objects.get_or_create(user_id=user.id)

        checks = Check.objects
        checks = checks.annotate(limit=F("project__owner__profile__ping_log_limit"))

        for check in checks:
            q = Ping.objects.filter(owner_id=check.id)
            q = q.filter(n__lte=check.n_pings - check.limit)
            q = q.filter(n__gt=0)
            n_pruned, _ = q.delete()

            self.stdout.write(
                "Pruned %d pings for check %s (%s)" % (n_pruned, check.id, check.name)
            )

        return "Done!"
