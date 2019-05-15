# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("api", "0006_check_grace")]

    operations = [
        migrations.CreateModel(
            name="Ping",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False,
                        auto_created=True,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("remote_addr", models.GenericIPAddressField()),
                ("method", models.CharField(max_length=10)),
                ("ua", models.CharField(max_length=100, blank=True)),
                ("body", models.TextField(blank=True)),
                ("owner", models.ForeignKey(to="api.Check", on_delete=models.CASCADE)),
            ],
        )
    ]
