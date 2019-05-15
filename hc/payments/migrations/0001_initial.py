# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.AutoField(
                        serialize=False,
                        primary_key=True,
                        auto_created=True,
                        verbose_name="ID",
                    ),
                ),
                ("customer_id", models.CharField(blank=True, max_length=36)),
                ("payment_method_token", models.CharField(blank=True, max_length=35)),
                ("subscription_id", models.CharField(blank=True, max_length=10)),
                (
                    "user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        to=settings.AUTH_USER_MODEL,
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
        )
    ]
