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
        self.flip.reason = "timeout"

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=True)
    def test_it_works(self, apprise: Mock) -> None:
        self.channel.notify(self.flip)
        self.assertEqual(Notification.objects.count(), 1)

        kwargs = apprise.return_value.notify.call_args.kwargs
        self.assertEqual(kwargs["title"], "Foo is DOWN")
        self.assertEqual(
            kwargs["body"],
            "Reason: success signal did not arrive on time, grace time passed.",
        )

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=False)
    def test_apprise_disabled(self, apprise: Mock) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Apprise is disabled and/or not installed")

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=True)
    def test_it_handles_reason_failure(self, apprise: Mock) -> None:
        self.flip.reason = "fail"
        self.channel.notify(self.flip)

        body = apprise.return_value.notify.call_args.kwargs["body"]
        self.assertEqual(body, "Reason: received a failure signal.")

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=True)
    def test_it_reports_down_duration(self, apprise: Mock) -> None:
        self.flip.save()

        up_flip = Flip(owner=self.check)
        up_flip.created = self.flip.created + td(minutes=90)
        up_flip.old_status = "down"
        up_flip.new_status = "up"
        self.channel.notify(up_flip)

        kwargs = apprise.return_value.notify.call_args.kwargs
        self.assertEqual(kwargs["title"], "Foo is UP")
        self.assertEqual(kwargs["body"], "The downtime lasted 1 hour, 30 minutes.")
