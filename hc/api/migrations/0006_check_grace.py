# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_auto_20150630_2021'),
    ]

    operations = [
        migrations.AddField(
            model_name='check',
            name='grace',
            field=models.DurationField(default=datetime.timedelta(0, 3600)),
        ),
    ]
