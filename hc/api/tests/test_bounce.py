from datetime import timedelta

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class BounceTestCase(BaseTestCase):

    def setUp(self):
        super(BounceTestCase, self).setUp()

        self.check = Check(user=self.alice, status="up")
        self.check.save()

        self.channel = Channel(user=self.alice, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

        self.n = Notification(owner=self.check, channel=self.channel)
        self.n.save()

    def test_it_works(self):
        url = "/api/v1/notifications/%s/bounce" % self.n.code
        r = self.client.post(url, "foo", content_type="text/plain")
        self.assertEqual(r.status_code, 200)

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "foo")

    def test_it_checks_ttl(self):
        self.n.created = self.n.created - timedelta(minutes=60)
        self.n.save()

        url = "/api/v1/notifications/%s/bounce" % self.n.code
        r = self.client.post(url, "foo", content_type="text/plain")
        self.assertEqual(r.status_code, 400)

    def test_it_handles_long_payload(self):
        url = "/api/v1/notifications/%s/bounce" % self.n.code
        payload = "A" * 500
        r = self.client.post(url, payload, content_type="text/plain")
        self.assertEqual(r.status_code, 200)
