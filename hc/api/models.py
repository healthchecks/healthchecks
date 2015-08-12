# coding: utf-8

from datetime import timedelta as td
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from hc.lib.emails import send

STATUSES = (("up", "Up"), ("down", "Down"), ("new", "New"))
DEFAULT_TIMEOUT = td(days=1)
DEFAULT_GRACE = td(hours=1)
CHANNEL_KINDS = (("email", "Email"), ("webhook", "Webhook"),
                 ("pd", "PagerDuty"))


class Check(models.Model):
    name = models.CharField(max_length=100, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    timeout = models.DurationField(default=DEFAULT_TIMEOUT)
    grace = models.DurationField(default=DEFAULT_GRACE)
    last_ping = models.DateTimeField(null=True, blank=True)
    alert_after = models.DateTimeField(null=True, blank=True, editable=False)
    status = models.CharField(max_length=6, choices=STATUSES, default="new")

    def __str__(self):
        return "Check(%s)" % self.code

    def url(self):
        return settings.PING_ENDPOINT + str(self.code)

    def email(self):
        return "%s@%s" % (self.code, settings.PING_EMAIL_DOMAIN)

    def send_alert(self):
        ctx = {
            "check": self,
            "checks": self.user.check_set.order_by("created"),
            "now": timezone.now()

        }

        if self.status in ("up", "down"):
            send(self.user.email, "emails/alert", ctx)
        else:
            raise NotImplemented("Unexpected status: %s" % self.status)

    def get_status(self):
        if self.status == "new":
            return "new"

        now = timezone.now()

        if self.last_ping + self.timeout > now:
            return "up"

        if self.last_ping + self.timeout + self.grace > now:
            return "grace"

        return "down"

    def assign_all_channels(self):
        for channel in Channel.objects.filter(user=self.user):
            channel.checks.add(self)
            channel.save()


class Ping(models.Model):
    owner = models.ForeignKey(Check)
    created = models.DateTimeField(auto_now_add=True)
    scheme = models.CharField(max_length=10, default="http")
    remote_addr = models.GenericIPAddressField(blank=True, null=True)
    method = models.CharField(max_length=10, blank=True)
    ua = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)


class Channel(models.Model):
    code = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=20, choices=CHANNEL_KINDS)
    value = models.CharField(max_length=200, blank=True)
    email_verified = models.BooleanField(default=False)
    checks = models.ManyToManyField(Check)
