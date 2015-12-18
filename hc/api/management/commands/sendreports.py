from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from hc.accounts.models import Profile
from hc.api.models import Check


def num_pinged_checks(profile):
    q = Check.objects.filter(user_id=profile.user.id,)
    q = q.filter(last_ping__isnull=False)
    return q.count()


class Command(BaseCommand):
    help = 'Send due monthly reports'

    def handle(self, *args, **options):
        # Create any missing profiles
        for u in User.objects.filter(profile__isnull=True):
            print("Creating profile for %s" % u.email)
            Profile.objects.for_user(u)

        now = timezone.now()
        month_before = now - timedelta(days=30)

        report_due = Q(next_report_date__lt=now)
        report_not_scheduled = Q(next_report_date__isnull=True)

        q = Profile.objects.filter(report_due | report_not_scheduled)
        q = q.filter(reports_allowed=True)
        q = q.filter(user__date_joined__lt=month_before)
        sent = 0
        for profile in q:
            if num_pinged_checks(profile) > 0:
                print("Sending monthly report to %s" % profile.user.email)
                profile.send_report()
                sent += 1

        print("Sent %d reports" % sent)
