# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from datetime import timedelta as td


class Migration(migrations.Migration):

    dependencies = [("api", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="check",
            name="alert_after",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="check", name="enabled", field=models.BooleanField(default=True)
        ),
        migrations.AddField(
            model_name="check",
            name="status",
            field=models.CharField(
                max_length=6,
                choices=[("up", "Up"), ("down", "Down"), ("new", "New")],
                default="new",
            ),
        ),
        migrations.AddField(
            model_name="check",
            name="timeout",
            field=models.DurationField(
                choices=[
                    (td(0, 300), "5 minutes"),
                    (td(0, 600), "10 minutes"),
                    (td(0, 1800), "30 minutes"),
                    (td(0, 3600), "1 hour"),
                    (td(0, 7200), "2 hours"),
                    (td(0, 21600), "6 hours"),
                    (td(0, 43200), "12 hours"),
                    (td(1), "1 day"),
                    (td(2), "2 days"),
                    (td(7), "1 week"),
                    (td(14), "2 weeks"),
                ],
                default=td(1),
            ),
        ),
    ]
