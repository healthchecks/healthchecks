from __future__ import annotations

from hc.api.models import Channel
from hc.test import BaseTestCase


class ListChannelsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.c1 = Channel(project=self.project)
        self.c1.kind = "email"
        self.c1.name = "Email to Alice"
        self.c1.save()

        self.url = "/api/v1/channels/"

    def get(self):
        return self.client.get(self.url, HTTP_X_API_KEY="X" * 32)

    def test_it_works(self):
        r = self.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        self.assertEqual(len(doc["channels"]), 1)

        c = doc["channels"][0]
        self.assertEqual(c["id"], str(self.c1.code))
        self.assertEqual(c["kind"], "email")
        self.assertEqual(c["name"], "Email to Alice")

    def test_it_handles_options(self):
        r = self.client.options(self.url)
        self.assertEqual(r.status_code, 204)
        self.assertIn("GET", r["Access-Control-Allow-Methods"])

    def test_it_shows_only_users_channels(self):
        Channel.objects.create(project=self.bobs_project, kind="email", name="Bob")

        r = self.get()
        data = r.json()
        self.assertEqual(len(data["channels"]), 1)
        for c in data["channels"]:
            self.assertNotEqual(c["name"], "Bob")

    def test_it_handles_missing_api_key(self):
        r = self.client.get(self.url)
        self.assertContains(r, "missing api key", status_code=401)

    def test_it_rejects_post(self):
        r = self.csrf_client.post(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 405)
