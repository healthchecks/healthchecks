# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("api", "0012_auto_20150930_1922")]

    operations = [
        migrations.AlterField(
            model_name="channel",
            name="kind",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("email", "Email"),
                    ("webhook", "Webhook"),
                    ("hipchat", "HipChat"),
                    ("slack", "Slack"),
                    ("pd", "PagerDuty"),
                ],
            ),
        )
    ]
