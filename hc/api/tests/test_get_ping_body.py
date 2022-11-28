from __future__ import annotations

from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class GetPingBodyTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project, name="Alice 1")
        self.check.n_pings = 1
        self.check.status = "up"
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.n = 1
        self.ping.body_raw = b"Foo\nBar\nBaz"
        self.ping.save()

        self.url = f"/api/v1/checks/{self.check.code}/pings/1/body"

    def test_it_allows_to_retrieve_bodies(self):
        r = self.client.get(self.url, HTTP_X_API_KEY=self.project.api_key)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "Foo\nBar\nBaz")
