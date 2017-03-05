# coding: utf-8

import hashlib
import json
import uuid
from datetime import datetime, timedelta as td

from croniter import croniter
from django.conf import settings
from django.core.checks import Warning
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone
from hc.api import transports
from hc.lib import emails

STATUSES = (
    ("up", "Up"),
    ("down", "Down"),
    ("new", "New"),
    ("paused", "Paused")
)
DEFAULT_TIMEOUT = td(days=1)
DEFAULT_GRACE = td(hours=1)
CHECK_KINDS = (("simple", "Simple"),
               ("cron", "Cron"))

CHANNEL_KINDS = (("email", "Email"),
                 ("webhook", "Webhook"),
                 ("hipchat", "HipChat"),
                 ("slack", "Slack"),
                 ("pd", "PagerDuty"),
                 ("po", "Pushover"),
                 ("pushbullet", "Pushbullet"),
                 ("opsgenie", "OpsGenie"),
                 ("victorops", "VictorOps"),
                 ("discord", "Discord"))

PO_PRIORITIES = {
    -2: "lowest",
    -1: "low",
    0: "normal",
    1: "high",
    2: "emergency"
}


class Check(models.Model):

    class Meta:
        # sendalerts command will query using these
        index_together = ["status", "user", "alert_after"]

    name = models.CharField(max_length=100, blank=True)
    tags = models.CharField(max_length=500, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    user = models.ForeignKey(User, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=10, default="simple",
                            choices=CHECK_KINDS)
    timeout = models.DurationField(default=DEFAULT_TIMEOUT)
    grace = models.DurationField(default=DEFAULT_GRACE)
    schedule = models.CharField(max_length=100, default="* * * * *")
    tz = models.CharField(max_length=36, default="UTC")
    n_pings = models.IntegerField(default=0)
    last_ping = models.DateTimeField(null=True, blank=True)
    alert_after = models.DateTimeField(null=True, blank=True, editable=False)
    status = models.CharField(max_length=6, choices=STATUSES, default="new")

    def name_then_code(self):
        if self.name:
            return self.name

        return str(self.code)

    def url(self):
        return settings.PING_ENDPOINT + str(self.code)

    def log_url(self):
        return settings.SITE_ROOT + reverse("hc-log", args=[self.code])

    def email(self):
        return "%s@%s" % (self.code, settings.PING_EMAIL_DOMAIN)

    def send_alert(self):
        if self.status not in ("up", "down"):
            raise NotImplementedError("Unexpected status: %s" % self.status)

        errors = []
        for channel in self.channel_set.all():
            error = channel.notify(self)
            if error not in ("", "no-op"):
                errors.append((channel, error))

        return errors

    def get_grace_start(self):
        """ Return the datetime when grace period starts. """

        # The common case, grace starts after timeout
        if self.kind == "simple":
            return self.last_ping + self.timeout

        # The complex case, next ping is expected based on cron schedule
        with timezone.override(self.tz):
            last_naive = timezone.make_naive(self.last_ping)
            it = croniter(self.schedule, last_naive)
            next_naive = it.get_next(datetime)
            return timezone.make_aware(next_naive, is_dst=False)

    def get_status(self, now=None):
        """ Return "up" if the check is up or in grace, otherwise "down". """

        if self.status in ("new", "paused"):
            return self.status

        if now is None:
            now = timezone.now()

        return "up" if self.get_grace_start() + self.grace > now else "down"

    def get_alert_after(self):
        """ Return the datetime when check potentially goes down. """

        return self.get_grace_start() + self.grace

    def in_grace_period(self):
        """ Return True if check is currently in grace period. """

        if self.status in ("new", "paused"):
            return False

        grace_start = self.get_grace_start()
        grace_end = grace_start + self.grace
        return grace_start < timezone.now() < grace_end

    def assign_all_channels(self):
        if self.user:
            channels = Channel.objects.filter(user=self.user)
            self.channel_set.add(*channels)

    def tags_list(self):
        return [t.strip() for t in self.tags.split(" ") if t.strip()]

    def to_dict(self):
        update_rel_url = reverse("hc-api-update", args=[self.code])
        pause_rel_url = reverse("hc-api-pause", args=[self.code])

        result = {
            "name": self.name,
            "ping_url": self.url(),
            "update_url": settings.SITE_ROOT + update_rel_url,
            "pause_url": settings.SITE_ROOT + pause_rel_url,
            "tags": self.tags,
            "grace": int(self.grace.total_seconds()),
            "n_pings": self.n_pings,
            "status": self.get_status()
        }

        if self.kind == "simple":
            result["timeout"] = int(self.timeout.total_seconds())
        elif self.kind == "cron":
            result["schedule"] = self.schedule
            result["tz"] = self.tz

        if self.last_ping:
            result["last_ping"] = self.last_ping.isoformat()
            result["next_ping"] = (self.last_ping + self.timeout).isoformat()
        else:
            result["last_ping"] = None
            result["next_ping"] = None

        return result

    @classmethod
    def check(cls, **kwargs):
        errors = super(Check, cls).check(**kwargs)

        trigger_detected = False
        try:
            dummy = Check(last_ping=timezone.now())
            dummy.save()
            dummy.refresh_from_db()
            trigger_detected = bool(dummy.alert_after)
            dummy.delete()
        except:
            pass

        if trigger_detected:
            err = Warning(
                "Obsolete 'update_alert_after' trigger exists in database.",
                hint="Please remove the trigger with 'manage.py droptriggers'",
                id="hc.api.E001")
            errors.append(err)

        return errors


class Ping(models.Model):
    n = models.IntegerField(null=True)
    owner = models.ForeignKey(Check)
    created = models.DateTimeField(auto_now_add=True)
    scheme = models.CharField(max_length=10, default="http")
    remote_addr = models.GenericIPAddressField(blank=True, null=True)
    method = models.CharField(max_length=10, blank=True)
    ua = models.CharField(max_length=200, blank=True)


class Channel(models.Model):
    code = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=20, choices=CHANNEL_KINDS)
    value = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    checks = models.ManyToManyField(Check)

    def assign_all_checks(self):
        checks = Check.objects.filter(user=self.user)
        self.checks.add(*checks)

    def make_token(self):
        seed = "%s%s" % (self.code, settings.SECRET_KEY)
        seed = seed.encode("utf8")
        return hashlib.sha1(seed).hexdigest()

    def send_verify_link(self):
        args = [self.code, self.make_token()]
        verify_link = reverse("hc-verify-email", args=args)
        verify_link = settings.SITE_ROOT + verify_link
        emails.verify_email(self.value, {"verify_link": verify_link})

    def get_unsub_link(self):
        args = [self.code, self.make_token()]
        verify_link = reverse("hc-unsubscribe-alerts", args=args)
        return settings.SITE_ROOT + verify_link

    @property
    def transport(self):
        if self.kind == "email":
            return transports.Email(self)
        elif self.kind == "webhook":
            return transports.Webhook(self)
        elif self.kind == "slack":
            return transports.Slack(self)
        elif self.kind == "hipchat":
            return transports.HipChat(self)
        elif self.kind == "pd":
            return transports.PagerDuty(self)
        elif self.kind == "victorops":
            return transports.VictorOps(self)
        elif self.kind == "pushbullet":
            return transports.Pushbullet(self)
        elif self.kind == "po":
            return transports.Pushover(self)
        elif self.kind == "opsgenie":
            return transports.OpsGenie(self)
        elif self.kind == "discord":
            return transports.Discord(self)
        else:
            raise NotImplementedError("Unknown channel kind: %s" % self.kind)

    def notify(self, check):
        if self.transport.is_noop(check):
            return "no-op"

        n = Notification(owner=check, channel=self)
        n.check_status = check.status
        n.error = "Sending"
        n.save()

        if self.kind == "email":
            error = self.transport.notify(check, n.bounce_url()) or ""
        else:
            error = self.transport.notify(check) or ""

        n.error = error
        n.save()

        return error

    @property
    def po_value(self):
        assert self.kind == "po"
        user_key, prio = self.value.split("|")
        prio = int(prio)
        return user_key, prio, PO_PRIORITIES[prio]

    @property
    def value_down(self):
        assert self.kind == "webhook"
        parts = self.value.split("\n")
        return parts[0]

    @property
    def value_up(self):
        assert self.kind == "webhook"
        parts = self.value.split("\n")
        return parts[1] if len(parts) > 1 else ""

    @property
    def post_data(self):
        assert self.kind == "webhook"
        parts = self.value.split("\n")
        return parts[2] if len(parts) > 2 else ""

    @property
    def slack_team(self):
        assert self.kind == "slack"
        if not self.value.startswith("{"):
            return None

        doc = json.loads(self.value)
        return doc["team_name"]

    @property
    def slack_channel(self):
        assert self.kind == "slack"
        if not self.value.startswith("{"):
            return None

        doc = json.loads(self.value)
        return doc["incoming_webhook"]["channel"]

    @property
    def slack_webhook_url(self):
        assert self.kind == "slack"
        if not self.value.startswith("{"):
            return self.value

        doc = json.loads(self.value)
        return doc["incoming_webhook"]["url"]

    @property
    def discord_webhook_url(self):
        assert self.kind == "discord"
        doc = json.loads(self.value)
        return doc["webhook"]["url"]

    @property
    def discord_webhook_id(self):
        assert self.kind == "discord"
        doc = json.loads(self.value)
        return doc["webhook"]["id"]

    def latest_notification(self):
        return Notification.objects.filter(channel=self).latest()


class Notification(models.Model):
    class Meta:
        get_latest_by = "created"

    code = models.UUIDField(default=uuid.uuid4, null=True, editable=False)
    owner = models.ForeignKey(Check)
    check_status = models.CharField(max_length=6)
    channel = models.ForeignKey(Channel)
    created = models.DateTimeField(auto_now_add=True)
    error = models.CharField(max_length=200, blank=True)

    def bounce_url(self):
        return settings.SITE_ROOT + reverse("hc-api-bounce", args=[self.code])
