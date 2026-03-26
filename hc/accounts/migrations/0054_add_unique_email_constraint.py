from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0053_alter_profile_user"),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique ON auth_user (LOWER(email)) WHERE email != ''",
            "DROP INDEX IF EXISTS auth_user_email_unique",
            # Reverse operation does nothing to avoid accidental data loss
        )
    ]