from datetime import timedelta

from django.utils import timezone
from hc.api.management.commands.prunepingsslow import Command
from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class PrunePingsSlowTestCase(BaseTestCase):
    year_ago = timezone.now() - timedelta(days=365)

    def test_it_removes_old_pings(self):
        self.profile.ping_log_limit = 1
        self.profile.save()

        c = Check(project=self.project, n_pings=2)
        c.save()

        Ping.objects.create(owner=c, n=1)
        Ping.objects.create(owner=c, n=2)

        Command().handle()

        self.assertEqual(Ping.objects.count(), 1)
