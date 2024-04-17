from __future__ import annotations

import time
from datetime import timedelta as td
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils.timezone import now

from hc.accounts.models import Profile
from hc.api.models import Channel, Check, Flip
from hc.lib import emails


class Command(BaseCommand):
    help = """Send warnings to accounts marked for deletion. """

    def pause(self) -> None:
        time.sleep(1)

    def members(self, user: User) -> QuerySet[User]:
        q = User.objects.filter(memberships__project__owner=user)
        q = q.exclude(last_login=None)
        return q.order_by("email")

    def send_channel_notifications(
        self, profile: Profile, skip_emails: list[str]
    ) -> None:
        # Sending deletion notices to configured notification channels is
        # a last ditch effort: only do this if 14 or fewer days are left.
        assert profile.deletion_scheduled_date
        delta = profile.deletion_scheduled_date - now()
        if delta.days > 14:
            return

        formatted = profile.deletion_scheduled_date.strftime("%B %-d, %Y")
        name = f"{settings.SITE_NAME} Account Deletion on {formatted}"
        desc = (
            f"The {settings.SITE_NAME} account registered to {profile.user.email} "
            f"is scheduled for deletion on {formatted}. To keep the account, "
            f"please contact {settings.SUPPORT_EMAIL} ASAP."
        )
        for channel in Channel.objects.filter(project__owner_id=profile.user_id):
            if channel.kind == "email" and channel.email.value in skip_emails:
                continue

            dummy = Check(name=name, desc=desc, status="down", project=channel.project)
            dummy.last_ping = now() - td(days=1)
            dummy.n_pings = 1

            dummy_flip = Flip(owner=dummy)
            dummy_flip.old_status = "up"
            dummy_flip.new_status = "down"

            self.stdout.write(f" * Sending notification to {channel.kind}")
            error = channel.notify(dummy_flip, is_test=True)
            if error == "no-op":
                # This channel may be configured to send "up" notifications only.
                dummy.status = "up"
                error = channel.notify(dummy_flip, is_test=True)

            if error:
                self.stdout.write(f"   Error sending notification: {error}")

    def handle(self, **options: Any) -> str:
        q = Profile.objects.order_by("id")
        q = q.filter(deletion_scheduled_date__gt=now())

        sent = 0
        for profile in q:
            recipients = [profile.user.email]
            # Include team members in the recipient list too:
            for u in self.members(profile.user):
                if u.email not in recipients:
                    recipients.append(u.email)

            self.stdout.write(f"Sending notice to {recipients}")
            ctx = {
                "owner_email": profile.user.email,
                "num_checks": profile.num_checks_used(),
                "support_email": settings.SUPPORT_EMAIL,
                "deletion_scheduled_date": profile.deletion_scheduled_date,
            }
            emails.deletion_scheduled(recipients, ctx)
            self.send_channel_notifications(profile, skip_emails=recipients)
            sent += 1

            # Throttle so we don't send too many emails at once:
            self.pause()

        return f"Done!\nNotices sent: {sent}\n"
