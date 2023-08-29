from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.management.commands.prunenotifications import Command
from hc.api.models import Channel, Check, Notification, Ping
from hc.test import BaseTestCase


class PruneNotificationsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Alice 1"
        self.check.n_pings = 101
        self.check.save()

        self.channel = Channel.objects.create(project=self.project)
        self.check.channel_set.add(self.channel)

    def test_it_works(self) -> None:
        p = Ping(owner=self.check)
        p.created = now()
        p.save()

        n = Notification.objects.create(owner=self.check, channel=self.channel)
        n.created = p.created - td(minutes=1)
        n.save()

        output = Command().handle()
        self.assertIn("Pruned 1 notifications", output)
        self.assertFalse(Notification.objects.exists())

    def test_it_handles_missing_pings(self) -> None:
        output = Command().handle()
        self.assertIn("Pruned 0 notifications", output)
