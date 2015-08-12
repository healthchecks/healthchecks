# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0009_auto_20150801_1250'),
    ]

    operations = [
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('code', models.UUIDField(editable=False, default=uuid.uuid4)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('kind', models.CharField(choices=[('email', 'Email'), ('webhook', 'Webhook'), ('pd', 'PagerDuty')], max_length=20)),
                ('value', models.CharField(max_length=200, blank=True)),
                ('email_verified', models.BooleanField(default=False)),
                ('checks', models.ManyToManyField(to='api.Check')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
