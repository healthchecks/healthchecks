from datetime import timedelta
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from hc.accounts.models import Profile, Member
from hc.api.models import Ping
from hc.lib import emails


class Command(BaseCommand):
    help = """Send deletion notices to inactive user accounts.

    Conditions for sending the notice:
        - deletion notice has not been sent recently
        - last login more than a year ago
        - none of the owned projects has invited team members

    """

    def handle(self, *args, **options):
        year_ago = now() - timedelta(days=365)

        q = Profile.objects.order_by("id")
        # Exclude accounts with logins in the last year_ago
        q = q.exclude(user__last_login__gt=year_ago)
        # Exclude accounts less than a year_ago old
        q = q.exclude(user__date_joined__gt=year_ago)
        # Exclude accounts with the deletion notice already sent
        q = q.exclude(deletion_notice_date__gt=year_ago)
        # Exclude paid accounts
        q = q.exclude(sms_limit__gt=0)

        sent = 0
        for profile in q:
            members = Member.objects.filter(project__owner_id=profile.user_id)
            if members.exists():
                print("Skipping %s, has team members" % profile)
                continue

            pings = Ping.objects
            pings = pings.filter(owner__project__owner_id=profile.user_id)
            pings = pings.filter(created__gt=year_ago)
            if pings.exists():
                print("Skipping %s, has pings in last year" % profile)
                continue

            self.stdout.write("Sending notice to %s" % profile.user.email)

            profile.deletion_notice_date = now()
            profile.save()

            ctx = {"email": profile.user.email, "support_email": settings.SUPPORT_EMAIL}
            emails.deletion_notice(profile.user.email, ctx)
            # Throttle so we don't send too many emails at once:
            time.sleep(1)
            sent += 1

        return "Done! Sent %d notices" % sent
