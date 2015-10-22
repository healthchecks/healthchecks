# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_auto_20151019_2039'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='check',
            index_together=set([('status', 'user', 'alert_after')]),
        ),
    ]
