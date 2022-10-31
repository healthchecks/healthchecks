# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from datetime import timedelta as td


class Migration(migrations.Migration):

    dependencies = [("api", "0005_auto_20150630_2021")]

    operations = [
        migrations.AddField(
            model_name="check",
            name="grace",
            field=models.DurationField(default=td(0, 3600)),
        )
    ]
