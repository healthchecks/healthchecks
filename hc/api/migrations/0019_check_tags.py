# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_remove_ping_body'),
    ]

    operations = [
        migrations.AddField(
            model_name='check',
            name='tags',
            field=models.CharField(max_length=500, blank=True),
        ),
    ]
