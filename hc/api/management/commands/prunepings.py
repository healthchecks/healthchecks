from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import F, Count

from hc.accounts.models import Profile
from hc.api.models import Check


class Command(BaseCommand):
    help = 'Prune pings based on limits in user profiles'

    def handle(self, *args, **options):
        # Create any missing user profiles
        for user in User.objects.filter(profile=None).iterator():
            Profile.objects.for_user(user)

        # Select checks having more pings than the limit in user profile
        checks = Check.objects
        checks = checks.annotate(
            limit=F("user__profile__ping_log_limit"),
            count_pings=Count("ping"))
        checks = checks.filter(count_pings__gt=F("limit"))
        checks = checks.select_related("user").order_by("user", "id")

        total = 0
        for check in checks.iterator():
            n = check.prune_pings(check.limit)
            total += n
            self.stdout.write("---")
            self.stdout.write("User:   %s" % check.user.email)
            self.stdout.write("Check:  %s" % check.name)
            self.stdout.write("Pruned: %d" % n)

        return "Done! Pruned %d pings." % total
