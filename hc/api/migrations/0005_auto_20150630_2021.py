# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [("api", "0004_auto_20150616_1319")]

    operations = [
        migrations.AlterField(
            model_name="check",
            name="user",
            field=models.ForeignKey(
                blank=True,
                to=settings.AUTH_USER_MODEL,
                null=True,
                on_delete=models.CASCADE,
            ),
        )
    ]
