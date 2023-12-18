from __future__ import annotations

import random
import uuid
from datetime import date, datetime
from datetime import timedelta as td
from secrets import token_urlsafe
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.signing import BadSignature, TimestampSigner
from django.db import models
from django.db.models import Q, QuerySet
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils.timezone import now

from hc.lib import emails
from hc.lib.date import month_boundaries, week_boundaries
from hc.lib.signing import sign_bounce_id

if TYPE_CHECKING:
    # Importing Check at runtime would cause a circular import, so only import it
    # during type checking
    from hc.api.models import Check

    CheckQuerySet = QuerySet[Check]


NO_NAG = td()
NAG_PERIODS = (
    (NO_NAG, "Disabled"),
    (td(hours=1), "Hourly"),
    (td(days=1), "Daily"),
)

REPORT_CHOICES = (("off", "Off"), ("weekly", "Weekly"), ("monthly", "Monthly"))
# How long an account can be over limits before it is scheduled for deletion
OVER_LIMIT_GRACE = td(days=31)
# When scheduling for deletion, how many days in the future to schedule
DELETION_GRACE = td(days=31)


def month(dt: datetime) -> date:
    """For a given datetime, return the matching first-day-of-month date."""
    return dt.date().replace(day=1)


class ProfileManager(models.Manager["Profile"]):
    def for_user(self, user: User) -> "Profile":
        try:
            return user.profile
        except Profile.DoesNotExist:
            profile = Profile(user=user)
            if not settings.USE_PAYMENTS:
                # If not using payments, set high limits
                profile.check_limit = 10000
                profile.sms_limit = 10000
                profile.call_limit = 10000
                profile.team_limit = 10000

            profile.save()
            return profile


class Profile(models.Model):
    user = models.OneToOneField(User, models.CASCADE)
    next_report_date = models.DateTimeField(null=True, blank=True)
    reports = models.CharField(max_length=10, default="monthly", choices=REPORT_CHOICES)
    nag_period = models.DurationField(default=NO_NAG, choices=NAG_PERIODS)
    next_nag_date = models.DateTimeField(null=True, blank=True)
    ping_log_limit = models.IntegerField(default=100)
    check_limit = models.IntegerField(default=20)
    token = models.CharField(max_length=128, blank=True)

    last_sms_date = models.DateTimeField(null=True, blank=True)
    sms_limit = models.IntegerField(default=5)
    sms_sent = models.IntegerField(default=0)

    last_call_date = models.DateTimeField(null=True, blank=True)
    call_limit = models.IntegerField(default=0)
    calls_sent = models.IntegerField(default=0)

    team_limit = models.IntegerField(default=2)
    sort = models.CharField(max_length=20, default="created")
    # The date when "Inactive Account Notification" is sent
    deletion_notice_date = models.DateTimeField(null=True, blank=True)
    # Set manually by admin, causes an orange banner in web UI
    deletion_scheduled_date = models.DateTimeField(null=True, blank=True)
    # If the account is over its check limit, the date when it went over the limit
    over_limit_date = models.DateTimeField(null=True, blank=True)
    last_active_date = models.DateTimeField(null=True, blank=True)
    tz = models.CharField(max_length=36, default="UTC")
    theme = models.CharField(max_length=10, null=True, blank=True)

    totp = models.CharField(max_length=32, null=True, blank=True)
    totp_created = models.DateTimeField(null=True, blank=True)

    objects = ProfileManager()

    def __str__(self) -> str:
        return f"Profile for {self.user.email}"

    def notifications_url(self) -> str:
        return settings.SITE_ROOT + reverse("hc-notifications")

    def reports_unsub_url(self) -> str:
        signer = TimestampSigner(salt="reports")
        signed_username = signer.sign(self.user.username)
        path = reverse("hc-unsubscribe-reports", args=[signed_username])
        return settings.SITE_ROOT + path

    def prepare_token(self) -> str:
        token = token_urlsafe(24)
        # Store a hashed transformation of the login token
        self.token = make_password(token, "login")
        self.save()
        # Sign the token so we can check its age later
        return TimestampSigner().sign(token)

    def check_token(self, token: str) -> bool:
        try:
            token = TimestampSigner().unsign(token, max_age=3600)
        except BadSignature:
            return False

        return "login" in self.token and check_password(token, self.token)

    def send_instant_login_link(
        self, membership: "Member" | None = None, redirect_url: str | None = None
    ) -> None:
        token = self.prepare_token()
        path = reverse("hc-check-token", args=[self.user.username, token])
        if redirect_url:
            path += "?next=%s" % redirect_url

        ctx = {
            "button_text": "Sign In",
            "button_url": settings.SITE_ROOT + path,
            "membership": membership,
        }
        emails.login(self.user.email, ctx)

    def send_change_email_link(self, new_email: str) -> None:
        payload = {
            "u": self.user.username,
            "t": self.prepare_token(),
            "e": new_email,
        }
        signed_payload = TimestampSigner().sign_object(payload)
        path = reverse("hc-change-email-verify", args=[signed_payload])

        ctx = {
            "button_text": "Sign In",
            "button_url": settings.SITE_ROOT + path,
        }
        emails.login(new_email, ctx)

    def send_transfer_request(self, project: "Project") -> None:
        token = self.prepare_token()
        settings_path = reverse("hc-project-settings", args=[project.code])
        path = reverse("hc-check-token", args=[self.user.username, token])
        path += "?next=%s" % settings_path

        ctx = {
            "button_text": "Project Settings",
            "button_url": settings.SITE_ROOT + path,
            "project": project,
        }
        emails.transfer_request(self.user.email, ctx)

    def send_sms_limit_notice(self, transport: str) -> None:
        ctx = {"transport": transport, "limit": self.sms_limit}
        if self.sms_limit != 500 and settings.USE_PAYMENTS:
            ctx["url"] = settings.SITE_ROOT + reverse("hc-pricing")

        emails.sms_limit(self.user.email, ctx)

    def send_call_limit_notice(self) -> None:
        ctx: dict[str, Any] = {"limit": self.call_limit}
        if self.call_limit != 500 and settings.USE_PAYMENTS:
            ctx["url"] = settings.SITE_ROOT + reverse("hc-pricing")

        emails.call_limit(self.user.email, ctx)

    def projects(self) -> QuerySet["Project"]:
        """Return a queryset of all projects we have access to."""

        is_owner = Q(owner_id=self.user_id)
        is_member = Q(member__user_id=self.user_id)
        q = Project.objects.filter(is_owner | is_member)
        return q.distinct().order_by(Lower("name"))

    def checks_from_all_projects(self) -> CheckQuerySet:
        """Return a queryset of checks from projects we have access to."""

        from hc.api.models import Check

        return Check.objects.filter(project__in=self.projects())

    def send_report(self, nag: bool = False) -> bool:
        q = self.checks_from_all_projects()

        # Has there been a ping in last 6 months?
        result = q.aggregate(models.Max("last_ping"))
        last_ping = result["last_ping__max"]

        six_months_ago = now() - td(days=180)
        if last_ping is None or last_ping < six_months_ago:
            return False

        # Sort checks by project. Need this because will group by project in template.
        q = q.select_related("project").order_by("project_id")
        # list() executes the query, to avoid DB access while rendering the template.
        checks = list(q)

        unsub_url = self.reports_unsub_url()
        headers = {
            "X-Bounce-ID": sign_bounce_id("r.%s" % self.user.username),
            "List-Unsubscribe": "<%s>" % unsub_url,
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
        ctx: dict[str, Any] = {
            "sort": self.sort,
            "unsub_link": unsub_url,
            "notifications_url": self.notifications_url(),
            "tz": self.tz,
        }

        if not nag:
            # For weekly and monthly reports, calculate the downtimes,
            # throw away the current period, keep two previous periods
            if self.reports == "weekly":
                boundaries = week_boundaries(3, self.tz)
            else:
                boundaries = month_boundaries(3, self.tz)

            for check in checks:
                downtimes = check.downtimes_by_boundary(boundaries, self.tz)
                # downtimes_by_boundary returns records in descending order,
                # but the template will need them in ascending order:
                downtimes.reverse()
                setattr(check, "past_downtimes", downtimes[:-1])

            # boundaries are in descending order, but the template
            # will need them in ascending order:
            boundaries.reverse()
            ctx["checks"] = checks
            ctx["boundaries"] = boundaries[:-1]
            ctx["monthly_or_weekly"] = self.reports
            emails.report(self.user.email, ctx, headers)

        if nag:
            # For nags, only show checks that are currently down
            checks = [c for c in checks if c.get_status() == "down"]
            if not checks:
                return False
            ctx["checks"] = checks
            ctx["num_down"] = len(checks)
            ctx["nag_period"] = self.nag_period.total_seconds()
            emails.nag(self.user.email, ctx, headers)

        return True

    def sms_sent_this_month(self) -> int:
        # IF last_sms_date was never set, we have not sent any messages yet.
        if not self.last_sms_date:
            return 0

        # If last sent date is not from this month, we've sent 0 this month.
        if month(now()) > month(self.last_sms_date):
            return 0

        return self.sms_sent

    def authorize_sms(self) -> bool:
        """If monthly limit not exceeded, increase counter and return True"""

        sent_this_month = self.sms_sent_this_month()
        if sent_this_month >= self.sms_limit:
            return False

        self.sms_sent = sent_this_month + 1
        self.last_sms_date = now()
        self.save()
        return True

    def calls_sent_this_month(self) -> int:
        # IF last_call_date was never set, we have not made any phone calls yet.
        if not self.last_call_date:
            return 0

        # If last sent date is not from this month, we've made 0 calls this month.
        if month(now()) > month(self.last_call_date):
            return 0

        return self.calls_sent

    def authorize_call(self) -> bool:
        """If monthly limit not exceeded, increase counter and return True"""

        sent_this_month = self.calls_sent_this_month()
        if sent_this_month >= self.call_limit:
            return False

        self.calls_sent = sent_this_month + 1
        self.last_call_date = now()
        self.save()
        return True

    def num_checks_used(self) -> int:
        from hc.api.models import Check

        return Check.objects.filter(project__owner_id=self.user_id).count()

    def num_checks_available(self) -> int:
        return self.check_limit - self.num_checks_used()

    def can_accept(self, project: "Project") -> bool:
        return project.num_checks() <= self.num_checks_available()

    def update_next_nag_date(self) -> None:
        any_down = self.checks_from_all_projects().filter(status="down").exists()
        if any_down and self.next_nag_date is None and self.nag_period:
            self.next_nag_date = now() + self.nag_period
            self.save(update_fields=["next_nag_date"])
        elif not any_down and self.next_nag_date:
            self.next_nag_date = None
            self.save(update_fields=["next_nag_date"])

    def choose_next_report_date(self) -> datetime | None:
        """Calculate the target date for the next monthly/weekly report.

        Monthly reports should get sent on 1st of each month, between
        9AM and 11AM in user's timezone.

        Weekly reports should get sent on Mondays, between
        9AM and 11AM in user's timezone.

        """

        if self.reports == "off":
            return None

        dt = now().astimezone(ZoneInfo(self.tz))
        dt = dt.replace(hour=9, minute=0) + td(minutes=random.randrange(0, 120))

        while True:
            dt += td(days=1)
            if self.reports == "monthly" and dt.day == 1:
                return dt
            elif self.reports == "weekly" and dt.weekday() == 0:
                return dt

    def is_past_over_limit_grace(self) -> bool:
        """Return True if this profile is over limits for 31 or more days."""
        if not self.over_limit_date:
            return False

        return now() > self.over_limit_date + OVER_LIMIT_GRACE

    def schedule_for_deletion(self) -> None:
        self.deletion_scheduled_date = now() + DELETION_GRACE
        self.save()


class Project(models.Model):
    code = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(User, models.CASCADE)
    api_key = models.CharField(max_length=128, blank=True, db_index=True)
    api_key_readonly = models.CharField(max_length=128, blank=True, db_index=True)
    badge_key = models.CharField(max_length=150, unique=True)
    ping_key = models.CharField(max_length=128, blank=True, null=True, unique=True)
    show_slugs = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name or self.owner.email

    @property
    def owner_profile(self) -> Profile:
        return Profile.objects.for_user(self.owner)

    def num_checks(self) -> int:
        return self.check_set.count()

    def num_checks_available(self) -> int:
        return self.owner_profile.num_checks_available()

    def invite_suggestions(self) -> QuerySet[User]:
        q = User.objects.filter(memberships__project__owner_id=self.owner_id)
        q = q.exclude(memberships__project=self)
        return q.distinct().order_by("email")

    def can_invite_new_users(self) -> bool:
        q = User.objects.filter(memberships__project__owner_id=self.owner_id)
        used = q.distinct().count()
        return used < self.owner_profile.team_limit

    def invite(self, user: User, role: str) -> bool:
        if Member.objects.filter(user=user, project=self).exists():
            return False

        if self.owner_id == user.id:
            return False

        m = Member.objects.create(user=user, project=self, role=role)
        checks_url = reverse("hc-checks", args=[self.code])

        if settings.EMAIL_HOST:
            profile = Profile.objects.for_user(user)
            profile.send_instant_login_link(membership=m, redirect_url=checks_url)
        return True

    def update_next_nag_dates(self) -> None:
        """Update next_nag_date on profiles of all members of this project."""

        is_owner = Q(user_id=self.owner_id)
        is_member = Q(user__memberships__project=self)
        q = Profile.objects.filter(is_owner | is_member).exclude(nag_period=NO_NAG)

        for profile in q:
            profile.update_next_nag_date()

        return None

    def get_n_down(self) -> int:
        result = 0
        for check in self.check_set.all():
            if check.get_status() == "down":
                result += 1

        return result

    def have_channel_issues(self) -> bool:
        errors = list(self.channel_set.values_list("last_error", flat=True))

        # It's a problem if a project has no integrations at all
        if len(errors) == 0:
            return True

        # It's a problem if any integration has a logged error
        return True if max(errors) else False

    def transfer_request(self) -> "Member" | None:
        return self.member_set.filter(transfer_request_date__isnull=False).first()

    def dashboard_url(self) -> str | None:
        if not self.api_key_readonly:
            return None

        frag = urlencode({self.api_key_readonly: str(self)}, quote_via=quote)
        return reverse("hc-dashboard") + "#" + frag

    def checks_url(self, full: bool = True) -> str:
        result = reverse("hc-checks", args=[self.code])
        return settings.SITE_ROOT + result if full else result

    def get_absolute_url(self) -> str:
        return self.checks_url(full=False)


class Member(models.Model):
    class Role(models.TextChoices):
        READONLY = "r", "Read-only"
        REGULAR = "w", "Member"
        MANAGER = "m", "Manager"

    user = models.ForeignKey(User, models.CASCADE, related_name="memberships")
    project = models.ForeignKey(Project, models.CASCADE)
    transfer_request_date = models.DateTimeField(null=True, blank=True)
    role = models.CharField(max_length=1, default=Role.REGULAR, choices=Role.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"], name="accounts_member_no_duplicates"
            )
        ]

    def can_accept(self) -> bool:
        return self.user.profile.can_accept(self.project)

    @property
    def is_rw(self) -> bool:
        return self.role in (Member.Role.REGULAR, Member.Role.MANAGER)


class Credential(models.Model):
    code = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, models.CASCADE, related_name="credentials")
    created = models.DateTimeField(auto_now_add=True)
    data = models.BinaryField()
