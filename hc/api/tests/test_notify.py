from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now
from hc.api.models import Channel, Check, Flip
from hc.test import BaseTestCase


class NotifyTestCase(BaseTestCase):
    def _setup_data(
        self, kind: str, value: str, status: str = "down", email_verified: bool = True
    ) -> None:
        self.check = Check(project=self.project)
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = kind
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = status

    def test_not_implemented(self) -> None:
        self._setup_data("webhook", "http://example")
        self.channel.kind = "invalid"

        with self.assertRaises(NotImplementedError):
            self.channel.notify(self.flip)
