# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest import skipIf
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase

try:
    import apprise

    have_apprise = bool(apprise)
except ImportError:
    have_apprise = False


@skipIf(not have_apprise, "apprise not installed")
class NotifyAppriseTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foo"
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now()
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.created = now() - td(minutes=10)
        self.ping.n = 112233
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "apprise"
        self.channel.value = "123"
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=True)
    def test_it_works(self, mock_apprise: Mock) -> None:
        mock_aobj = Mock()
        mock_aobj.add.return_value = True
        mock_aobj.notify.return_value = True
        mock_apprise.return_value = mock_aobj
        self.channel.notify(self.flip)
        self.assertEqual(Notification.objects.count(), 1)

        body = mock_apprise.return_value.notify.call_args.kwargs["body"]
        self.assertIn("Foo is DOWN", body)
        self.assertIn("Last ping was 10 minutes ago.", body)

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=False)
    def test_apprise_disabled(self, mock_apprise: Mock) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Apprise is disabled and/or not installed")

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=True)
    def test_it_handles_no_last_ping(self, mock_apprise: Mock) -> None:
        self.ping.delete()

        mock_aobj = Mock()
        mock_aobj.add.return_value = True
        mock_aobj.notify.return_value = True
        mock_apprise.return_value = mock_aobj
        self.channel.notify(self.flip)

        body = mock_apprise.return_value.notify.call_args.kwargs["body"]
        self.assertIn("Foo is DOWN", body)
        self.assertNotIn("Last ping was", body)
