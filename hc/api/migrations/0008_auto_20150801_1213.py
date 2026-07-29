from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0007_ping")]

    operations = [
        migrations.AlterField(
            model_name="ping",
            name="ua",
            field=models.CharField(max_length=200, blank=True),
        )
    ]
