from __future__ import annotations

import json

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip
from hc.test import BaseTestCase


class FlipModelTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.channel = Channel.objects.create(project=self.project, kind="email")
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "up"
        self.flip.new_status = "down"

    def test_select_channels_works(self):
        channels = self.flip.select_channels()
        self.assertEqual(channels, [self.channel])

    def test_select_channels_handles_noop(self):
        self.channel.value = json.dumps({"down": False})
        self.channel.save()

        channels = self.flip.select_channels()
        self.assertEqual(channels, [])

    def test_send_alerts_handles_new_up_transition(self):
        self.flip.old_status = "new"
        self.flip.new_status = "up"

        channels = self.flip.select_channels()
        self.assertEqual(channels, [])

    def test_it_skips_disabled_channels(self):
        self.channel.disabled = True
        self.channel.save()

        channels = self.flip.select_channels()
        self.assertEqual(channels, [])
