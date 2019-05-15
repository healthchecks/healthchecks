# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("api", "0008_auto_20150801_1213")]

    operations = [
        migrations.AddField(
            model_name="ping",
            name="scheme",
            field=models.CharField(max_length=10, default="http"),
        ),
        migrations.AlterField(
            model_name="ping",
            name="method",
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AlterField(
            model_name="ping",
            name="remote_addr",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
    ]
