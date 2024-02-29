# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest import skipIf
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
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
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "apprise"
        self.channel.value = "123"
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=True)
    def test_it_works(self, mock_apprise: Mock) -> None:
        mock_aobj = Mock()
        mock_aobj.add.return_value = True
        mock_aobj.notify.return_value = True
        mock_apprise.return_value = mock_aobj
        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

        body = mock_apprise.return_value.notify.call_args.kwargs["body"]
        self.assertIn("Foo is DOWN", body)
        self.assertIn("Last ping was an hour ago.", body)

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=False)
    def test_apprise_disabled(self, mock_apprise: Mock) -> None:
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Apprise is disabled and/or not installed")

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=True)
    def test_it_handles_no_last_ping(self, mock_apprise: Mock) -> None:
        self.check.last_ping = None
        self.check.save()

        mock_aobj = Mock()
        mock_aobj.add.return_value = True
        mock_aobj.notify.return_value = True
        mock_apprise.return_value = mock_aobj
        self.channel.notify(self.check)

        body = mock_apprise.return_value.notify.call_args.kwargs["body"]
        self.assertIn("Foo is DOWN", body)
        self.assertNotIn("Last ping was", body)
