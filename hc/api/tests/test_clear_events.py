from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class ClearEventsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check.objects.create(project=self.project, status="down")
        self.check.last_ping = now()
        self.check.last_start = now()
        self.check.last_duration = td(seconds=5)
        self.check.has_confirmation_link = True
        self.check.alert_after = now()
        self.check.save()

        Ping.objects.create(owner=self.check, n=1)
        channel = Channel.objects.create(project=self.project, kind="email")
        Notification.objects.create(
            owner=self.check, channel=channel, check_status="down"
        )
        Flip.objects.create(owner=self.check, created=now(), old_status="up", new_status="down")

        self.url = f"/api/v3/checks/{self.check.code}/events/clear"

    def test_it_works(self) -> None:
        r = self.csrf_client.post(
            self.url, "", content_type="application/json", HTTP_X_API_KEY="X" * 32
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "new")
        self.assertIsNone(self.check.last_ping)
        self.assertIsNone(self.check.last_start)
        self.assertIsNone(self.check.last_duration)
        self.assertFalse(self.check.has_confirmation_link)
        self.assertIsNone(self.check.alert_after)

        self.assertFalse(self.check.ping_set.exists())
        self.assertFalse(self.check.notification_set.exists())
        self.assertFalse(self.check.flip_set.exists())

    def test_it_accepts_api_key_in_post_body(self) -> None:
        payload = {"api_key": "X" * 32}
        r = self.csrf_client.post(self.url, payload, content_type="application/json")
        self.assertEqual(r.status_code, 200)

    def test_it_handles_options(self) -> None:
        r = self.client.options(self.url)
        self.assertEqual(r.status_code, 204)
        self.assertIn("POST", r["Access-Control-Allow-Methods"])

    def test_it_only_allows_post(self) -> None:
        r = self.client.get(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 405)

    def test_it_validates_ownership(self) -> None:
        check = Check.objects.create(project=self.bobs_project, status="down")
        url = f"/api/v3/checks/{check.code}/events/clear"
        r = self.client.post(
            url, "", content_type="application/json", HTTP_X_API_KEY="X" * 32
        )
        self.assertEqual(r.status_code, 403)

    def test_it_validates_uuid(self) -> None:
        url = "/api/v3/checks/not-uuid/events/clear"
        r = self.client.post(
            url, "", content_type="application/json", HTTP_X_API_KEY="X" * 32
        )
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_check(self) -> None:
        url = "/api/v3/checks/07c2f548-9850-4b27-af5d-6c9dc157ec02/events/clear"
        r = self.client.post(
            url, "", content_type="application/json", HTTP_X_API_KEY="X" * 32
        )
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_non_dict_post_body(self) -> None:
        r = self.csrf_client.post(self.url, "123", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            r.json()["error"], "json validation error: value is not an object"
        )
