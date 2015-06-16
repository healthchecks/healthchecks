# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_auto_20150616_0732'),
    ]

    operations = [
        migrations.AddField(
            model_name='check',
            name='name',
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.AlterField(
            model_name='check',
            name='alert_after',
            field=models.DateTimeField(editable=False, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='check',
            name='timeout',
            field=models.DurationField(default=datetime.timedelta(1)),
        ),
    ]
