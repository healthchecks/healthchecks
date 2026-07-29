from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0004_auto_20150616_1319")]

    operations = [
        migrations.AlterField(
            model_name="check",
            name="user",
            field=models.ForeignKey(
                blank=True,
                to=settings.AUTH_USER_MODEL,
                null=True,
                on_delete=models.CASCADE,
            ),
        )
    ]
