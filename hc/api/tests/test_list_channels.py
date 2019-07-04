import json

from hc.api.models import Channel
from hc.test import BaseTestCase


class ListChannelsTestCase(BaseTestCase):
    def setUp(self):
        super(ListChannelsTestCase, self).setUp()

        self.c1 = Channel(project=self.project)
        self.c1.kind = "email"
        self.c1.name = "Email to Alice"
        self.c1.save()

    def get(self):
        return self.client.get("/api/v1/channels/", HTTP_X_API_KEY="X" * 32)

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
        r = self.client.options("/api/v1/channels/")
        self.assertEqual(r.status_code, 204)
        self.assertIn("GET", r["Access-Control-Allow-Methods"])

    def test_it_shows_only_users_channels(self):
        Channel.objects.create(project=self.bobs_project, kind="email", name="Bob")

        r = self.get()
        data = r.json()
        self.assertEqual(len(data["channels"]), 1)
        for c in data["channels"]:
            self.assertNotEqual(c["name"], "Bob")

    def test_it_accepts_api_key_from_request_body(self):
        payload = json.dumps({"api_key": "X" * 32})
        r = self.client.generic(
            "GET", "/api/v1/channels/", payload, content_type="application/json"
        )

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Email to Alice")
