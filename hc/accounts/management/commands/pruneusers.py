from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone


class Command(BaseCommand):
    help = """Prune old, inactive user accounts.

    Conditions for removing an user account:
        - created 1+ month ago and never logged in.
          Use case: visitor types in their email at the website but
          never follows through with login.

        - not logged in for 1 month, and has no checks
          Use case: user wants to remove their account. So they
          remove all checks and leave the account at that.

    """

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=31)

        # Old accounts, never logged in
        q = User.objects
        q = q.filter(date_joined__lt=cutoff, last_login=None)
        n1, _ = q.delete()

        # Not logged in for 1 month, 0 checks
        q = User.objects
        q = q.annotate(n_checks=Count("check"))
        q = q.filter(last_login__lt=cutoff, n_checks=0)
        n2, _ = q.delete()

        return "Done! Pruned %d user accounts." % (n1 + n2)
