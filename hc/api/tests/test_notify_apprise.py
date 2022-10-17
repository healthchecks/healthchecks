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
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
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
    def test_apprise_enabled(self, mock_apprise):
        mock_aobj = Mock()
        mock_aobj.add.return_value = True
        mock_aobj.notify.return_value = True
        mock_apprise.return_value = mock_aobj
        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

        self.check.status = "up"
        self.assertEqual(Notification.objects.count(), 1)

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=False)
    def test_apprise_disabled(self, mock_apprise):
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Apprise is disabled and/or not installed")
