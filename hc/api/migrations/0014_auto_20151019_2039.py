# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [("api", "0013_auto_20151001_2029")]

    operations = [
        migrations.AlterField(
            model_name="check",
            name="code",
            field=models.UUIDField(default=uuid.uuid4, db_index=True, editable=False),
        )
    ]
