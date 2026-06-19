from __future__ import annotations

import json
from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip
from hc.test import BaseTestCase


class FlipModelTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.channel = Channel.objects.create(project=self.project, kind="email")
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "up"
        self.flip.new_status = "down"

    def test_select_channels_works(self) -> None:
        channels = self.flip.select_channels()
        self.assertEqual(channels, [self.channel])

    def test_select_channels_handles_noop(self) -> None:
        self.channel.value = json.dumps(
            {"value": "alice@example.org", "up": False, "down": False}
        )
        self.channel.save()

        channels = self.flip.select_channels()
        self.assertEqual(channels, [])

    def test_select_channels_validates_new_status(self) -> None:
        self.flip.new_status = "paused"
        with self.assertRaises(NotImplementedError):
            self.flip.select_channels()

    def test_send_alerts_handles_new_up_transition(self) -> None:
        self.flip.old_status = "new"
        self.flip.new_status = "up"

        channels = self.flip.select_channels()
        self.assertEqual(channels, [])

    def test_it_skips_disabled_channels(self) -> None:
        self.channel.disabled = True
        self.channel.save()

        channels = self.flip.select_channels()
        self.assertEqual(channels, [])

    def test_it_sorts_channels_by_last_notify_duration(self) -> None:
        c1 = Channel.objects.create(
            project=self.project, kind="email", last_notify_duration=td(seconds=1)
        )
        c1.checks.add(self.check)
        c9 = Channel.objects.create(
            project=self.project, kind="email", last_notify_duration=td(seconds=9)
        )
        c9.checks.add(self.check)

        channels = self.flip.select_channels()
        self.assertEqual(channels, [c1, c9, self.channel])

    def test_it_calculates_down_duration(self) -> None:
        self.flip.save()

        up_flip = Flip(owner=self.check)
        up_flip.created = self.flip.created + td(minutes=10)
        up_flip.old_status = "down"
        up_flip.new_status = "up"

        self.assertEqual(up_flip.down_duration, td(minutes=10))

    def test_down_duration_asserts_flips_status(self) -> None:
        with self.assertRaises(AssertionError):
            self.flip.down_duration

    def test_down_duration_checks_prev_flips_status(self) -> None:
        self.flip.old_status = "down"
        self.flip.new_status = "up"
        self.flip.save()

        up_flip = Flip(owner=self.check)
        up_flip.created = self.flip.created + td(minutes=10)
        up_flip.old_status = "down"
        up_flip.new_status = "up"

        self.assertIsNone(up_flip.down_duration)

    def test_down_duration_handles_unsaved_check(self) -> None:
        check = Check(project=self.project)
        flip = Flip(owner=check)
        flip.created = now()
        flip.old_status = "down"
        flip.new_status = "up"

        # The check is not saved, and does not have a primary key.
        # down_duration cannot fetch its flips and should return None.
        self.assertIsNone(flip.down_duration)
