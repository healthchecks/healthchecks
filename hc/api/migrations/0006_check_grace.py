from datetime import timedelta as td

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0005_auto_20150630_2021")]

    operations = [
        migrations.AddField(
            model_name="check",
            name="grace",
            field=models.DurationField(default=td(0, 3600)),
        )
    ]
