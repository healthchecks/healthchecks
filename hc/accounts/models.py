from base64 import urlsafe_b64encode
from datetime import timedelta
import os
import uuid

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.signing import TimestampSigner
from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from hc.lib import emails
from hc.lib.date import month_boundaries


NO_NAG = timedelta()
NAG_PERIODS = (
    (NO_NAG, "Disabled"),
    (timedelta(hours=1), "Hourly"),
    (timedelta(days=1), "Daily"),
)


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
    user = models.OneToOneField(User, models.CASCADE, blank=True, null=True)
    next_report_date = models.DateTimeField(null=True, blank=True)
    reports_allowed = models.BooleanField(default=True)
    nag_period = models.DurationField(default=NO_NAG, choices=NAG_PERIODS)
    next_nag_date = models.DateTimeField(null=True, blank=True)
    ping_log_limit = models.IntegerField(default=100)
    check_limit = models.IntegerField(default=20)
    token = models.CharField(max_length=128, blank=True)
    current_project = models.ForeignKey("Project", models.SET_NULL, null=True)
    last_sms_date = models.DateTimeField(null=True, blank=True)
    sms_limit = models.IntegerField(default=0)
    sms_sent = models.IntegerField(default=0)
    team_limit = models.IntegerField(default=2)
    sort = models.CharField(max_length=20, default="created")
    deletion_notice_date = models.DateTimeField(null=True, blank=True)

    objects = ProfileManager()

    def __str__(self):
        return "Profile for %s" % self.user.email

    def notifications_url(self):
        return settings.SITE_ROOT + reverse("hc-notifications")

    def reports_unsub_url(self):
        signer = TimestampSigner(salt="reports")
        signed_username = signer.sign(self.user.username)
        path = reverse("hc-unsubscribe-reports", args=[signed_username])
        return settings.SITE_ROOT + path

    def prepare_token(self, salt):
        token = urlsafe_b64encode(os.urandom(24)).decode()
        self.token = make_password(token, salt)
        self.save()
        return token

    def check_token(self, token, salt):
        return salt in self.token and check_password(token, self.token)

    def send_instant_login_link(self, inviting_project=None, redirect_url=None):
        token = self.prepare_token("login")
        path = reverse("hc-check-token", args=[self.user.username, token])
        if redirect_url:
            path += "?next=%s" % redirect_url

        ctx = {
            "button_text": "Sign In",
            "button_url": settings.SITE_ROOT + path,
            "inviting_project": inviting_project,
        }
        emails.login(self.user.email, ctx)

    def send_set_password_link(self):
        token = self.prepare_token("set-password")
        path = reverse("hc-set-password", args=[token])
        ctx = {"button_text": "Set Password", "button_url": settings.SITE_ROOT + path}
        emails.set_password(self.user.email, ctx)

    def send_change_email_link(self):
        token = self.prepare_token("change-email")
        path = reverse("hc-change-email", args=[token])
        ctx = {"button_text": "Change Email", "button_url": settings.SITE_ROOT + path}
        emails.change_email(self.user.email, ctx)

    def projects(self):
        """ Return a queryset of all projects we have access to. """

        is_owner = Q(owner=self.user)
        is_member = Q(member__user=self.user)
        q = Project.objects.filter(is_owner | is_member)
        return q.distinct().order_by("name")

    def annotated_projects(self):
        """ Return all projects, annotated with 'n_down'. """

        # Subquery for getting project ids
        project_ids = self.projects().values("id")

        # Main query with the n_down annotation.
        # Must use the subquery, otherwise ORM gets confused by
        # joins and group by's
        q = Project.objects.filter(id__in=project_ids)
        n_down = Count("check", filter=Q(check__status="down"))
        q = q.annotate(n_down=n_down)
        return q.order_by("name")

    def checks_from_all_projects(self):
        """ Return a queryset of checks from projects we have access to. """

        project_ids = self.projects().values("id")

        from hc.api.models import Check

        return Check.objects.filter(project_id__in=project_ids)

    def send_report(self, nag=False):
        checks = self.checks_from_all_projects()

        # Has there been a ping in last 6 months?
        result = checks.aggregate(models.Max("last_ping"))
        last_ping = result["last_ping__max"]

        six_months_ago = timezone.now() - timedelta(days=180)
        if last_ping is None or last_ping < six_months_ago:
            return False

        # Is there at least one check that is down?
        num_down = checks.filter(status="down").count()
        if nag and num_down == 0:
            return False

        # Sort checks by project. Need this because will group by project in
        # template.
        checks = checks.select_related("project")
        checks = checks.order_by("project_id")
        # list() executes the query, to avoid DB access while
        # rendering the template
        checks = list(checks)

        unsub_url = self.reports_unsub_url()

        headers = {"List-Unsubscribe": unsub_url, "X-Bounce-Url": unsub_url}

        ctx = {
            "checks": checks,
            "sort": self.sort,
            "now": timezone.now(),
            "unsub_link": unsub_url,
            "notifications_url": self.notifications_url(),
            "nag": nag,
            "nag_period": self.nag_period.total_seconds(),
            "num_down": num_down,
            "month_boundaries": month_boundaries(),
        }

        emails.report(self.user.email, ctx, headers)
        return True

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


class Project(models.Model):
    code = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(User, models.CASCADE)
    api_key = models.CharField(max_length=128, blank=True, db_index=True)
    api_key_readonly = models.CharField(max_length=128, blank=True, db_index=True)
    badge_key = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name or self.owner.email

    @property
    def owner_profile(self):
        return Profile.objects.for_user(self.owner)

    def num_checks_available(self):
        from hc.api.models import Check

        num_used = Check.objects.filter(project__owner=self.owner).count()
        return self.owner_profile.check_limit - num_used

    def set_api_keys(self):
        self.api_key = urlsafe_b64encode(os.urandom(24)).decode()
        self.api_key_readonly = urlsafe_b64encode(os.urandom(24)).decode()
        self.save()

    def can_invite(self):
        return self.member_set.count() < self.owner_profile.team_limit

    def invite(self, user):
        Member.objects.create(user=user, project=self)

        # Switch the invited user over to the new team so they
        # notice the new team on next visit:
        user.profile.current_project = self
        user.profile.save()

        user.profile.send_instant_login_link(self)

    def set_next_nag_date(self):
        """ Set next_nag_date on profiles of all members of this project. """

        is_owner = Q(user=self.owner)
        is_member = Q(user__memberships__project=self)
        q = Profile.objects.filter(is_owner | is_member)
        q = q.exclude(nag_period=NO_NAG)
        # Exclude profiles with next_nag_date already set
        q = q.filter(next_nag_date__isnull=True)

        q.update(next_nag_date=timezone.now() + models.F("nag_period"))

    def overall_status(self):
        status = "up"
        for check in self.check_set.all():
            check_status = check.get_status(with_started=False)
            if status == "up" and check_status == "grace":
                status = "grace"

            if check_status == "down":
                status = "down"
                break
        return status


class Member(models.Model):
    user = models.ForeignKey(User, models.CASCADE, related_name="memberships")
    project = models.ForeignKey(Project, models.CASCADE)
