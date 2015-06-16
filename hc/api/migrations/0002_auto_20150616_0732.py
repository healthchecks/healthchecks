# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='check',
            name='alert_after',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='check',
            name='enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='check',
            name='status',
            field=models.CharField(max_length=6, choices=[('up', 'Up'), ('down', 'Down'), ('new', 'New')], default='new'),
        ),
        migrations.AddField(
            model_name='check',
            name='timeout',
            field=models.DurationField(choices=[(datetime.timedelta(0, 300), '5 minutes'), (datetime.timedelta(0, 600), '10 minutes'), (datetime.timedelta(0, 1800), '30 minutes'), (datetime.timedelta(0, 3600), '1 hour'), (datetime.timedelta(0, 7200), '2 hours'), (datetime.timedelta(0, 21600), '6 hours'), (datetime.timedelta(0, 43200), '12 hours'), (datetime.timedelta(1), '1 day'), (datetime.timedelta(2), '2 days'), (datetime.timedelta(7), '1 week'), (datetime.timedelta(14), '2 weeks')], default=datetime.timedelta(1)),
        ),
    ]
