from django.db import migrations, models
from hc.accounts.models import Member


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0042_remove_member_rw"),
    ]

    operations = [
        migrations.AlterField(
            model_name="member",
            name="role",
            field=models.CharField(
                choices=Member.Role.choices, default=Member.Role.REGULAR, max_length=1
            ),
        ),
    ]
