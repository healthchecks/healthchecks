# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td

from django.core import mail
from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification
from hc.test import BaseTestCase


class NotifyGroupTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foobar"
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now()
        self.check.save()

        self.channel_email = Channel(project=self.project)
        self.channel_email.kind = "email"
        self.channel_email.value = "alice@example.org"
        self.channel_email.email_verified = True
        self.channel_email.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "group"
        self.channel.value = f"{self.channel_email.code}"
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"

    def test_it_works(self) -> None:
        self.channel.notify(self.flip)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "")

        # There should be two notifications, one for the group,
        # and the other for the group member
        notifications = list(Notification.objects.order_by("id"))
        self.assertEqual(len(notifications), 2)
        self.assertEqual(notifications[0].channel, self.channel)
        self.assertEqual(notifications[1].channel, self.channel_email)

        # An email should have been sent
        self.assertEqual(len(mail.outbox), 1)

    def test_it_handles_noop(self) -> None:
        self.channel_email.value = json.dumps(
            {"value": "alice@example.org", "up": False, "down": False}
        )
        self.channel_email.save()

        self.channel.notify(self.flip)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "")

        n = Notification.objects.get()
        self.assertEqual(n.channel, self.channel)
        self.assertEqual(n.error, "")

    def test_it_ignores_invalid_channels(self) -> None:
        self.channel.value = (
            "bda20a83-409c-4b2c-8e9b-589d408cd57b,40500bf8-0f37-4bb3-970c-9fe64b7ef39d"
        )
        self.channel.save()

        self.channel.notify(self.flip)

        self.channel.refresh_from_db()
        assert self.channel.last_error == ""

        n = Notification.objects.get()
        self.assertEqual(n.channel, self.channel)
        self.assertEqual(n.error, "")

    @override_settings(SHELL_ENABLED=True)
    def test_it_reports_failure_count(self) -> None:
        self.channel_email.email_verified = False
        self.channel_email.save()

        self.channel.notify(self.flip)

        self.channel.refresh_from_db()
        assert self.channel.last_error == "1 out of 1 notifications failed"
