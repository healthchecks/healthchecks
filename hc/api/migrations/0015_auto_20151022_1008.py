from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("api", "0014_auto_20151019_2039")]
    # This migration used to add an index using index_together.
    # index_together is gone in Django 5.1, and we don't need it
    # anyway because a later migration removes this index.
    # So this migration now does nothing.
    operations = []
