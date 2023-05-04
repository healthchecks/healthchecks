# -*- coding: utf-8 -*-
from __future__ import annotations, unicode_literals

import datetime
from datetime import timezone

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0003_auto_20150616_1249")]

    operations = [
        migrations.RemoveField(model_name="check", name="enabled"),
        migrations.AddField(
            model_name="check",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True,
                default=datetime.datetime(
                    2015, 6, 16, 13, 19, 17, 218278, tzinfo=timezone.utc
                ),
            ),
            preserve_default=False,
        ),
    ]
