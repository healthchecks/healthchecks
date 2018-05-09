from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone


class Command(BaseCommand):
    help = """Prune old, inactive user accounts.

    Conditions for removing an user account:
        - created 1 month ago and never logged in. Does not belong
          to any team.
          Use case: visitor types in their email at the website but
          never follows through with login.

    """

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=30)

        # Old accounts, never logged in, no team memberships
        q = User.objects.order_by("id")
        q = q.annotate(n_teams=Count("memberships"))
        q = q.filter(date_joined__lt=cutoff, last_login=None, n_teams=0)

        n, summary = q.delete()
        return "Done! Pruned %d user accounts." % summary.get("auth.User", 0)
