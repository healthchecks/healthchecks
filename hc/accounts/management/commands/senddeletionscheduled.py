from __future__ import annotations

import time

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from hc.accounts.models import Profile
from hc.lib import emails


class Command(BaseCommand):
    help = """Send warnings to accounts marked for deletion. """

    def pause(self):
        time.sleep(1)

    def members(self, user):
        q = User.objects.filter(memberships__project__owner=user)
        q = q.exclude(last_login=None)
        return q.order_by("email")

    def handle(self, *args, **options):
        q = Profile.objects.order_by("id")
        q = q.filter(deletion_scheduled_date__gt=now())

        sent = 0
        for profile in q:
            recipients = [profile.user.email]
            # Include team members in the recipient list too:
            for u in self.members(profile.user):
                recipients.append(u.email)

            for recipient in recipients:
                role = "owner" if recipient == profile.user.email else "member"
                self.stdout.write(f"Sending notice to {recipient} ({role})")
                ctx = {
                    "owner_email": profile.user.email,
                    "num_checks": profile.num_checks_used(),
                    "support_email": settings.SUPPORT_EMAIL,
                    "deletion_scheduled_date": profile.deletion_scheduled_date,
                }
                emails.deletion_scheduled(recipient, ctx)
                sent += 1

                # Throttle so we don't send too many emails at once:
                self.pause()

        return f"Done!\nNotices sent: {sent}\n"
