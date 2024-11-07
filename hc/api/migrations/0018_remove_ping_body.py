
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("api", "0017_auto_20151117_1032")]

    operations = [migrations.RemoveField(model_name="ping", name="body")]
