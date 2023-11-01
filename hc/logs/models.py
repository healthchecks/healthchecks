from __future__ import annotations

import logging

from django.db import models
from django.utils.timezone import now

LEVELS = [
    (logging.NOTSET, "notset"),
    (logging.DEBUG, "debug"),
    (logging.INFO, "info"),
    (logging.WARNING, "warning"),
    (logging.ERROR, "error"),
    (logging.CRITICAL, "critical"),
]


class Record(models.Model):
    created = models.DateTimeField(default=now)
    name = models.CharField(max_length=100)
    level = models.PositiveSmallIntegerField(choices=LEVELS)
    message = models.TextField()
    traceback = models.TextField()
