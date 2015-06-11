import uuid

from django.contrib.auth.models import User
from django.db import models


class Canary(models.Model):
    class Meta:
        verbose_name_plural = "canaries"

    code = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User)
    last_ping = models.DateTimeField(null=True, blank=True)
