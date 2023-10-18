from __future__ import annotations

import time
from datetime import timedelta as td
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.timezone import now

from hc.accounts.models import Member, Profile
from hc.api.models import Ping
from hc.lib import emails

YEAR_AGO = now() - td(days=365)


def has_projects_with_active_members(profile: Profile) -> bool:
    q = Member.objects.filter(project__owner_id=profile.user_id)
    recent_signup = Q(user__date_joined__gt=YEAR_AGO)
    recent_login = Q(user__last_login__gt=YEAR_AGO)
    recent_activity = Q(user__profile__last_active_date__gt=YEAR_AGO)
    q = q.filter(recent_signup | recent_login | recent_activity)
    return q.exists()


class Command(BaseCommand):
    help = """Send deletion notices to inactive user accounts.

    Conditions for sending the notice:
        - deletion notice has not been sent recently
        - last login more than a year ago
        - none of the owned projects has active team members
        - none of the owned projects has pings in the last year
        - is on a free plan

    """

    def pause(self) -> None:
        time.sleep(1)

    def handle(self, **options: Any) -> str:
        q = Profile.objects.order_by("id")
        # Exclude accounts with logins in the last year
        q = q.exclude(user__last_login__gt=YEAR_AGO)
        # Exclude accounts less than a year old
        q = q.exclude(user__date_joined__gt=YEAR_AGO)
        # Exclude accounts with the deletion notice already sent
        q = q.exclude(deletion_notice_date__gt=YEAR_AGO)
        # Exclude accounts with activity in the last year
        q = q.exclude(last_active_date__gt=YEAR_AGO)
        # Exclude accounts with subscriptions
        q = q.exclude(user__subscription__subscription_id__gt="")

        sent = 0
        skipped_has_team = 0
        skipped_has_pings = 0

        for profile in q:
            if has_projects_with_active_members(profile):
                # Don't send deletion notice: this account has team members
                skipped_has_team += 1
                continue

            pings = Ping.objects.filter(owner__project__owner_id=profile.user_id)
            pings = pings.filter(created__gt=YEAR_AGO)
            if pings.exists():
                # Don't send deletion notice: this account has pings in the last year
                skipped_has_pings += 1
                continue

            self.stdout.write("Sending notice to %s" % profile.user.email)

            profile.deletion_notice_date = now()
            profile.save()

            ctx = {"email": profile.user.email, "support_email": settings.SUPPORT_EMAIL}
            emails.deletion_notice(profile.user.email, ctx)
            sent += 1

            # Throttle so we don't send too many emails at once:
            self.pause()

        return (
            f"Done!\n"
            f"* Notices sent: {sent}\n"
            f"* Skipped (has team members): {skipped_has_team}\n"
            f"* Skipped (has pings in the last year): {skipped_has_pings}\n"
        )
