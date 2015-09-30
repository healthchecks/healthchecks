# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_notification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channel',
            name='kind',
            field=models.CharField(choices=[('email', 'Email'), ('webhook', 'Webhook'), ('slack', 'Slack'), ('pd', 'PagerDuty')], max_length=20),
        ),
    ]
