from __future__ import annotations

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


@override_settings(METRICS_KEY="foo")
class MetricsTestCase(BaseTestCase):
    url = "/api/v1/metrics/"

    def test_it_returns_num_unprocessed_flips(self) -> None:
        check = Check.objects.create(project=self.project, status="down")
        flip = Flip(owner=check)
        flip.created = now()
        flip.old_status = "up"
        flip.new_status = "down"
        flip.save()

        r = self.client.get(self.url, HTTP_X_METRICS_KEY="foo")
        self.assertEqual(r.status_code, 200)

        doc = r.json()
        self.assertEqual(doc["num_unprocessed_flips"], 1)

    def test_it_returns_max_ping_id(self) -> None:
        check = Check.objects.create(project=self.project, status="down")
        ping = Ping.objects.create(owner=check, n=1)

        r = self.client.get(self.url, HTTP_X_METRICS_KEY="foo")
        self.assertEqual(r.status_code, 200)

        doc = r.json()
        self.assertEqual(doc["max_ping_id"], ping.id)

    def test_it_returns_max_notification_id(self) -> None:
        check = Check.objects.create(project=self.project, status="down")
        channel = Channel.objects.create(project=self.project, kind="email")
        n = Notification.objects.create(
            owner=check, channel=channel, check_status="down"
        )

        r = self.client.get(self.url, HTTP_X_METRICS_KEY="foo")
        self.assertEqual(r.status_code, 200)

        doc = r.json()
        self.assertEqual(doc["max_notification_id"], n.id)

    @override_settings(METRICS_KEY=None)
    def test_it_handles_unset_metrics_key(self) -> None:
        r = self.client.get(self.url, HTTP_X_METRICS_KEY="foo")
        self.assertEqual(r.status_code, 403)

    def test_it_handles_incorrect_metrics_key(self) -> None:
        r = self.client.get(self.url, HTTP_X_METRICS_KEY="bar")
        self.assertEqual(r.status_code, 403)
