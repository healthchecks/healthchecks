from __future__ import annotations

from unittest.mock import patch

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

    @patch("hc.api.models.Channel.notify")
    def test_send_alerts_works(self, mock_notify):
        mock_notify.return_value = ""

        results = list(self.flip.send_alerts())
        self.assertEqual(len(results), 1)

        ch, error, send_time = results[0]
        self.assertEqual(ch, self.channel)
        self.assertEqual(error, "")

    @patch("hc.api.models.Channel.notify")
    def test_send_alerts_handles_error(self, mock_notify):
        mock_notify.return_value = "something went wrong"

        results = list(self.flip.send_alerts())
        self.assertEqual(len(results), 1)

        ch, error, send_time = results[0]
        self.assertEqual(error, "something went wrong")

    @patch("hc.api.models.Channel.notify")
    def test_send_alerts_handles_noop(self, mock_notify):

        mock_notify.return_value = "no-op"

        results = list(self.flip.send_alerts())
        self.assertEqual(results, [])

    @patch("hc.api.models.Channel.notify")
    def test_send_alerts_handles_new_up_transition(self, mock_notify):
        self.flip.old_status = "new"
        self.flip.new_status = "up"

        results = list(self.flip.send_alerts())
        self.assertEqual(results, [])

    def test_it_skips_disabled_channels(self):
        self.channel.disabled = True
        self.channel.save()

        results = list(self.flip.send_alerts())
        self.assertEqual(results, [])
