# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("api", "0015_auto_20151022_1008")]

    operations = [
        migrations.AlterField(
            model_name="check",
            name="status",
            field=models.CharField(
                default="new",
                max_length=6,
                choices=[
                    ("up", "Up"),
                    ("down", "Down"),
                    ("new", "New"),
                    ("paused", "Paused"),
                ],
            ),
        )
    ]
