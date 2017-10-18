from base64 import urlsafe_b64encode
import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.signing import TimestampSigner
from django.db import models
from django.urls import reverse
from django.utils import timezone
from hc.lib import emails


NO_NAG = timedelta()
NAG_PERIODS = ((NO_NAG, "Disabled"),
               (timedelta(hours=1), "Hourly"),
               (timedelta(days=1), "Daily"))


def month(dt):
    """ For a given datetime, return the matching first-day-of-month date. """
    return dt.date().replace(day=1)


class ProfileManager(models.Manager):
    def for_user(self, user):
        try:
            return user.profile
        except Profile.DoesNotExist:
            profile = Profile(user=user)
            if not settings.USE_PAYMENTS:
                # If not using payments, set high limits
                profile.check_limit = 500
                profile.sms_limit = 500
                profile.team_limit = 500

            profile.save()
            return profile


class Profile(models.Model):
    # Owner:
    user = models.OneToOneField(User, models.CASCADE, blank=True, null=True)
    team_name = models.CharField(max_length=200, blank=True)
    next_report_date = models.DateTimeField(null=True, blank=True)
    reports_allowed = models.BooleanField(default=True)
    nag_period = models.DurationField(default=NO_NAG, choices=NAG_PERIODS)
    next_nag_date = models.DateTimeField(null=True, blank=True)
    ping_log_limit = models.IntegerField(default=100)
    check_limit = models.IntegerField(default=20)
    token = models.CharField(max_length=128, blank=True)
    api_key = models.CharField(max_length=128, blank=True)
    current_team = models.ForeignKey("self", models.SET_NULL, null=True)
    bill_to = models.TextField(blank=True)
    last_sms_date = models.DateTimeField(null=True, blank=True)
    sms_limit = models.IntegerField(default=0)
    sms_sent = models.IntegerField(default=0)
    team_limit = models.IntegerField(default=2)
    sort = models.CharField(max_length=20, default="created")

    objects = ProfileManager()

    def __str__(self):
        return self.team_name or self.user.email

    def notifications_url(self):
        return settings.SITE_ROOT + reverse("hc-notifications")

    def reports_unsub_url(self):
        signer = TimestampSigner(salt="reports")
        signed_username = signer.sign(self.user.username)
        path = reverse("hc-unsubscribe-reports", args=[signed_username])
        return settings.SITE_ROOT + path

    def team(self):
        # compare ids to avoid SQL queries
        if self.current_team_id and self.current_team_id != self.id:
            return self.current_team

        return self

    def prepare_token(self, salt):
        token = urlsafe_b64encode(os.urandom(24)).decode("utf-8")
        self.token = make_password(token, salt)
        self.save()
        return token

    def check_token(self, token, salt):
        return salt in self.token and check_password(token, self.token)

    def send_instant_login_link(self, inviting_profile=None):
        token = self.prepare_token("login")
        path = reverse("hc-check-token", args=[self.user.username, token])
        ctx = {
            "button_text": "Log In",
            "button_url": settings.SITE_ROOT + path,
            "inviting_profile": inviting_profile
        }
        emails.login(self.user.email, ctx)

    def send_set_password_link(self):
        token = self.prepare_token("set-password")
        path = reverse("hc-set-password", args=[token])
        ctx = {
            "button_text": "Set Password",
            "button_url": settings.SITE_ROOT + path
        }
        emails.set_password(self.user.email, ctx)

    def send_change_email_link(self):
        token = self.prepare_token("change-email")
        path = reverse("hc-change-email", args=[token])
        ctx = {
            "button_text": "Change Email",
            "button_url": settings.SITE_ROOT + path
        }
        emails.change_email(self.user.email, ctx)

    def set_api_key(self):
        self.api_key = urlsafe_b64encode(os.urandom(24))
        self.save()

    def checks_from_all_teams(self):
        """ Return a queryset of checks from all teams we have access for. """

        team_ids = set(self.user.memberships.values_list("team_id", flat=True))
        team_ids.add(self.id)

        from hc.api.models import Check
        return Check.objects.filter(user__profile__id__in=team_ids)

    def send_report(self, nag=False):
        checks = self.checks_from_all_teams()

        # Is there at least one check that has received a ping?
        if not checks.filter(last_ping__isnull=False).exists():
            return False

        # Is there at least one check that is down?
        num_down = checks.filter(status="down").count()
        if nag and num_down == 0:
            return False

        # Sort checks by owner. Need this because will group by owner in
        # template.
        checks = checks.order_by("user_id")

        ctx = {
            "checks": checks,
            "sort": self.sort,
            "now": timezone.now(),
            "unsub_link": self.reports_unsub_url(),
            "notifications_url": self.notifications_url(),
            "nag": nag,
            "nag_period": self.nag_period.total_seconds(),
            "num_down": num_down
        }

        emails.report(self.user.email, ctx)
        return True

    def can_invite(self):
        return self.member_set.count() < self.team_limit

    def invite(self, user):
        member = Member(team=self, user=user)
        member.save()

        # Switch the invited user over to the new team so they
        # notice the new team on next visit:
        user.profile.current_team = self
        user.profile.save()

        user.profile.send_instant_login_link(self)

    def sms_sent_this_month(self):
        # IF last_sms_date was never set, we have not sent any messages yet.
        if not self.last_sms_date:
            return 0

        # If last sent date is not from this month, we've sent 0 this month.
        if month(timezone.now()) > month(self.last_sms_date):
            return 0

        return self.sms_sent

    def authorize_sms(self):
        """ If monthly limit not exceeded, increase counter and return True """

        sent_this_month = self.sms_sent_this_month()
        if sent_this_month >= self.sms_limit:
            return False

        self.sms_sent = sent_this_month + 1
        self.last_sms_date = timezone.now()
        self.save()
        return True

    def set_next_nag_date(self):
        """ Set next_nag_date for all members of this team. """

        is_owner = models.Q(id=self.id)
        is_member = models.Q(user__memberships__team=self)
        q = Profile.objects.filter(is_owner | is_member)
        q = q.exclude(nag_period=NO_NAG)
        # Exclude profiles with next_nag_date already set
        q = q.filter(next_nag_date__isnull=True)

        q.update(next_nag_date=timezone.now() + models.F("nag_period"))


class Member(models.Model):
    team = models.ForeignKey(Profile, models.CASCADE)
    user = models.ForeignKey(User, models.CASCADE, related_name="memberships")
