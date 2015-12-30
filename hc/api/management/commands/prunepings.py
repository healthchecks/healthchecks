from django.db.models import F
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from hc.accounts.models import Profile
from hc.api.models import Check


class Command(BaseCommand):
    help = 'Prune pings based on limits in user profiles'

    def handle(self, *args, **options):

        # Create any missing user profiles
        for user in User.objects.filter(profile=None):
            Profile.objects.for_user(user)

        # Select checks having n_ping greater than the limit in user profile
        checks = Check.objects
        checks = checks.annotate(limit=F("user__profile__ping_log_limit"))
        checks = checks.filter(n_pings__gt=F("limit"))

        for check in checks:
            n = check.prune_pings(check.limit)
            print("---")
            print("User:   %s" % check.user.email)
            print("Check:  %s" % check.name)
            print("Pruned: %d" % n)

        print("Done.")
