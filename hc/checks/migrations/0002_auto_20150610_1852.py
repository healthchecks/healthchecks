# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('checks', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='canary',
            options={'verbose_name_plural': 'canaries'},
        ),
        migrations.AddField(
            model_name='canary',
            name='last_ping',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
