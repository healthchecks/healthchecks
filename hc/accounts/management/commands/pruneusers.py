from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count, F
from django.utils.timezone import now
from hc.accounts.models import Profile


class Command(BaseCommand):
    help = """Prune old, inactive user accounts.

    Conditions for removing an user account:
        - created 1 month ago and never logged in. Does not belong
          to any team.
          Use case: visitor types in their email at the website but
          never follows through with login.

    """

    def handle(self, *args, **options):
        month_ago = now() - timedelta(days=30)

        # Old accounts, never logged in, no team memberships
        q = User.objects.order_by("id")
        q = q.annotate(n_teams=Count("memberships"))
        q = q.filter(date_joined__lt=month_ago, last_login=None, n_teams=0)

        n, summary = q.delete()
        count = summary.get("auth.User", 0)
        self.stdout.write("Pruned %d never-logged-in user accounts." % count)

        # Profiles scheduled for deletion
        q = Profile.objects.order_by("id")
        q = q.filter(deletion_notice_date__lt=month_ago)
        # Exclude users who have logged in after receiving deletion notice
        q = q.exclude(user__last_login__gt=F("deletion_notice_date"))

        for profile in q:
            self.stdout.write("Deleting inactive %s" % profile.user.email)
            profile.user.delete()

        return "Done!"
