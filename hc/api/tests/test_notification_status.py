from __future__ import annotations

from datetime import timedelta as td

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotificationStatusTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project, status="up")
        self.check.save()

        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.email_verified = True
        self.channel.save()

        self.n = Notification(owner=self.check, channel=self.channel)
        self.n.save()

        self.url = "/api/v1/notifications/%s/status" % self.n.code

    def test_it_handles_twilio_failed_status(self) -> None:
        r = self.csrf_client.post(self.url, {"MessageStatus": "failed"})
        self.assertEqual(r.status_code, 200)

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "Delivery failed (status=failed).")

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "Delivery failed (status=failed).")
        self.assertTrue(self.channel.email_verified)

    def test_it_handles_twilio_undelivered_status(self) -> None:
        r = self.csrf_client.post(self.url, {"MessageStatus": "undelivered"})
        self.assertEqual(r.status_code, 200)

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "Delivery failed (status=undelivered).")

        self.channel.refresh_from_db()
        self.assertIn("status=undelivered", self.channel.last_error)

    def test_it_handles_twilio_delivered_status(self) -> None:
        r = self.csrf_client.post(self.url, {"MessageStatus": "delivered"})
        self.assertEqual(r.status_code, 200)

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "")

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "")

    def test_it_checks_ttl(self) -> None:
        self.n.created = self.n.created - td(minutes=61)
        self.n.save()

        r = self.csrf_client.post(self.url, {"MessageStatus": "failed"})
        self.assertEqual(r.status_code, 200)

        # The notification should not have the error field set:
        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "")

    def test_it_handles_missing_notification(self) -> None:
        fake_code = "07c2f548-9850-4b27-af5d-6c9dc157ec02"
        url = f"/api/v1/notifications/{fake_code}/status"
        r = self.csrf_client.post(url, {"MessageStatus": "failed"})
        self.assertEqual(r.status_code, 200)

    def test_it_requires_post(self) -> None:
        r = self.csrf_client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_handles_error_key(self) -> None:
        r = self.csrf_client.post(self.url, {"error": "Something went wrong."})
        self.assertEqual(r.status_code, 200)

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "Something went wrong.")

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "Something went wrong.")
        self.assertTrue(self.channel.email_verified)

    def test_it_handles_mark_disabled_key(self) -> None:
        payload = {"error": "Received complaint.", "mark_disabled": "1"}

        r = self.csrf_client.post(self.url, payload)
        self.assertEqual(r.status_code, 200)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "Received complaint.")
        self.assertTrue(self.channel.email_verified)
        self.assertTrue(self.channel.disabled)

    def test_it_handles_twilio_call_status_failed(self) -> None:
        r = self.csrf_client.post(self.url, {"CallStatus": "failed"})
        self.assertEqual(r.status_code, 200)

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "Delivery failed (status=failed).")

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "Delivery failed (status=failed).")
        self.assertTrue(self.channel.email_verified)
