from datetime import timedelta as td
import uuid

from django.contrib.auth.models import User
from django.db import models

STATUSES = (("up", "Up"), ("down", "Down"), ("new", "New"))
DEFAULT_TIMEOUT = td(days=1)


class Check(models.Model):
    name = models.CharField(max_length=100, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    timeout = models.DurationField(default=DEFAULT_TIMEOUT)
    last_ping = models.DateTimeField(null=True, blank=True)
    alert_after = models.DateTimeField(null=True, blank=True, editable=False)
    status = models.CharField(max_length=6, choices=STATUSES, default="new")
