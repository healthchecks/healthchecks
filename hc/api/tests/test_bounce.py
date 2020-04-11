from datetime import timedelta

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class BounceTestCase(BaseTestCase):
    def setUp(self):
        super(BounceTestCase, self).setUp()

        self.check = Check(project=self.project, status="up")
        self.check.save()

        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.email_verified = True
        self.channel.save()

        self.n = Notification(owner=self.check, channel=self.channel)
        self.n.save()

    def test_it_works(self):
        url = "/api/v1/notifications/%s/bounce" % self.n.code
        r = self.client.post(url, "foo", content_type="text/plain")
        self.assertEqual(r.status_code, 200)

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "foo")

        self.channel.refresh_from_db()
        self.assertFalse(self.channel.email_verified)
        self.assertEqual(self.channel.last_error, "foo")

    def test_it_checks_ttl(self):
        self.n.created = self.n.created - timedelta(minutes=60)
        self.n.save()

        url = "/api/v1/notifications/%s/bounce" % self.n.code
        r = self.client.post(url, "foo", content_type="text/plain")
        self.assertEqual(r.status_code, 403)

    def test_it_handles_long_payload(self):
        url = "/api/v1/notifications/%s/bounce" % self.n.code
        payload = "A" * 500
        r = self.client.post(url, payload, content_type="text/plain")
        self.assertEqual(r.status_code, 200)

    def test_it_handles_missing_notification(self):
        fake_code = "07c2f548-9850-4b27-af5d-6c9dc157ec02"
        url = "/api/v1/notifications/%s/bounce" % fake_code
        r = self.client.post(url, "", content_type="text/plain")
        self.assertEqual(r.status_code, 404)

    def test_it_requires_post(self):
        url = "/api/v1/notifications/%s/bounce" % self.n.code
        r = self.client.get(url)
        self.assertEqual(r.status_code, 405)

    def test_does_not_unsubscribe_transient_bounces(self):
        url = "/api/v1/notifications/%s/bounce?type=Transient" % self.n.code
        self.client.post(url, "foo", content_type="text/plain")

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "foo")

        self.channel.refresh_from_db()
        self.assertTrue(self.channel.email_verified)
