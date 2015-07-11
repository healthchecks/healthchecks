from datetime import timedelta as td
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from hc.lib.emails import send

STATUSES = (("up", "Up"), ("down", "Down"), ("new", "New"))
DEFAULT_TIMEOUT = td(days=1)
TIMEOUT_CHOICES = (
    ("15 minutes", td(minutes=15)),
    ("30 minutes", td(minutes=30)),
    ("1 hour", td(hours=1)),
    ("3 hours", td(hours=3)),
    ("6 hours", td(hours=6)),
    ("12 hours", td(hours=12)),
    ("1 day", td(days=1)),
    ("2 days", td(days=2)),
    ("3 days", td(days=3)),
    ("1 week", td(weeks=1))
)


class Check(models.Model):
    name = models.CharField(max_length=100, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    timeout = models.DurationField(default=DEFAULT_TIMEOUT)
    last_ping = models.DateTimeField(null=True, blank=True)
    alert_after = models.DateTimeField(null=True, blank=True, editable=False)
    status = models.CharField(max_length=6, choices=STATUSES, default="new")

    def url(self):
        return settings.PING_ENDPOINT + str(self.code)

    def send_alert(self):
        ctx = {
            "timeout_choices": TIMEOUT_CHOICES,
            "check": self,
            "checks": self.user.check_set.order_by("created"),
            "now": timezone.now()

        }

        if self.status in ("up", "down"):
            send(self.user.email, "emails/alert", ctx)
        else:
            raise NotImplemented("Unexpected status: %s" % self.status)
