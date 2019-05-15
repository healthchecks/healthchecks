# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("payments", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="plan_id",
            field=models.CharField(blank=True, max_length=10),
        )
    ]
