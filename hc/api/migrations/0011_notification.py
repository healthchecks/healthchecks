# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("api", "0010_channel")]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.AutoField(
                        serialize=False,
                        auto_created=True,
                        verbose_name="ID",
                        primary_key=True,
                    ),
                ),
                ("check_status", models.CharField(max_length=6)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("status", models.IntegerField(default=0)),
                (
                    "channel",
                    models.ForeignKey(to="api.Channel", on_delete=models.CASCADE),
                ),
                ("owner", models.ForeignKey(to="api.Check", on_delete=models.CASCADE)),
            ],
        )
    ]
