from datetime import timedelta as td

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0002_auto_20150616_0732")]

    operations = [
        migrations.AddField(
            model_name="check",
            name="name",
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.AlterField(
            model_name="check",
            name="alert_after",
            field=models.DateTimeField(editable=False, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="check",
            name="timeout",
            field=models.DurationField(default=td(1)),
        ),
    ]
