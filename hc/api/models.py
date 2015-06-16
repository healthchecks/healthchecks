from datetime import timedelta as td
import uuid

from django.contrib.auth.models import User
from django.db import models

STATUSES = (("up", "Up"), ("down", "Down"), ("new", "New"))
ONEDAY = td(days=1)
DURATIONS = (
    (td(minutes=5),  "5 minutes"),
    (td(minutes=10), "10 minutes"),
    (td(minutes=30), "30 minutes"),
    (td(hours=1),    "1 hour"),
    (td(hours=2),    "2 hours"),
    (td(hours=6),    "6 hours"),
    (td(hours=12),   "12 hours"),
    (ONEDAY,         "1 day"),
    (td(days=2),     "2 days"),
    (td(weeks=1),    "1 week"),
    (td(weeks=2),    "2 weeks")
)


class Check(models.Model):
    name = models.CharField(max_length=100, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    timeout = models.DurationField(default=ONEDAY)
    last_ping = models.DateTimeField(null=True, blank=True)
    alert_after = models.DateTimeField(null=True, blank=True, editable=False)
    status = models.CharField(max_length=6, choices=STATUSES, default="new")
