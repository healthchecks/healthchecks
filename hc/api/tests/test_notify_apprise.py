# coding: utf-8

from datetime import timedelta as td
from unittest import skipIf
from unittest.mock import patch, Mock

from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase
from django.test.utils import override_settings

try:
    import apprise
except ImportError:
    apprise = None


@skipIf(apprise is None, "apprise not installed")
class NotifyTestCase(BaseTestCase):
    def _setup_data(self, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "apprise"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=True)
    def test_apprise_enabled(self, mock_apprise):
        self._setup_data("123")

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
        self._setup_data("123")

        mock_aobj = Mock()
        mock_aobj.add.return_value = True
        mock_aobj.notify.return_value = True
        mock_apprise.return_value = mock_aobj
        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)
