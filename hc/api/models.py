# coding: utf-8

from datetime import timedelta as td
import hashlib
import json
import uuid

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
import requests

from hc.lib import emails


STATUSES = (("up", "Up"), ("down", "Down"), ("new", "New"))
DEFAULT_TIMEOUT = td(days=1)
DEFAULT_GRACE = td(hours=1)
CHANNEL_KINDS = (("email", "Email"), ("webhook", "Webhook"),
                 ("slack", "Slack"), ("pd", "PagerDuty"))


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

    def name_then_code(self):
        if self.name:
            return self.name

        return str(self.code)

    def url(self):
        return settings.PING_ENDPOINT + str(self.code)

    def email(self):
        return "%s@%s" % (self.code, settings.PING_EMAIL_DOMAIN)

    def send_alert(self):
        if self.status not in ("up", "down"):
            raise NotImplemented("Unexpected status: %s" % self.status)

        for channel in self.channel_set.all():
            channel.notify(self)

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
        if self.user:
            channels = Channel.objects.filter(user=self.user)
            self.channel_set.add(*channels)


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

    def make_token(self):
        seed = "%s%s" % (self.code, settings.SECRET_KEY)
        seed = seed.encode("utf8")
        return hashlib.sha1(seed).hexdigest()

    def send_verify_link(self):
        args = [self.code, self.make_token()]
        verify_link = reverse("hc-verify-email", args=args)
        verify_link = settings.SITE_ROOT + verify_link
        emails.verify_email(self.value, {"verify_link": verify_link})

    def notify(self, check):
        n = Notification(owner=check, channel=self)
        n.check_status = check.status

        if self.kind == "email" and self.email_verified:
            ctx = {
                "check": check,
                "checks": self.user.check_set.order_by("created"),
                "now": timezone.now()
            }
            emails.alert(self.value, ctx)
            n.save()
        elif self.kind == "webhook" and check.status == "down":
            try:
                r = requests.get(self.value, timeout=5)
                n.status = r.status_code
            except requests.exceptions.Timeout:
                # Well, we tried
                pass

            n.save()
        elif self.kind == "slack":
            text = render_to_string("slack_message.html", {"check": check})
            payload = {
                "text": text,
                "username": "healthchecks.io",
                "icon_url": "https://healthchecks.io/static/img/logo@2x.png"
            }

            r = requests.post(self.value, data=json.dumps(payload))

            n.status = r.status_code
            n.save()

        elif self.kind == "pd":
            if check.status == "down":
                event_type = "trigger"
                description = "%s is DOWN" % check.name_then_code()
            else:
                event_type = "resolve"
                description = "%s received a ping and is now UP" % \
                    check.name_then_code()

            payload = {
                "service_key": self.value,
                "incident_key": str(check.code),
                "event_type": event_type,
                "description": description,
                "client": "healthchecks.io",
                "client_url": settings.SITE_ROOT
            }

            url = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"
            r = requests.post(url, data=json.dumps(payload))

            n.status = r.status_code
            n.save()


class Notification(models.Model):
    owner = models.ForeignKey(Check)
    check_status = models.CharField(max_length=6)
    channel = models.ForeignKey(Channel)
    created = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=0)
