# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_auto_20151030_1107'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channel',
            name='kind',
            field=models.CharField(choices=[('email', 'Email'), ('webhook', 'Webhook'), ('hipchat', 'HipChat'), ('slack', 'Slack'), ('pd', 'PagerDuty'), ('po', 'Pushover')], max_length=20),
        ),
    ]
