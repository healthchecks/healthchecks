import json
from datetime import timedelta as td
from django.utils.timezone import now
from django.conf import settings

from hc.api.models import Check
from hc.test import BaseTestCase


class ListChecksTestCase(BaseTestCase):

    def setUp(self):
        super(ListChecksTestCase, self).setUp()

        self.now = now().replace(microsecond=0)

        self.a1 = Check(user=self.alice, name="Alice 1")
        self.a1.timeout = td(seconds=3600)
        self.a1.grace = td(seconds=900)
        self.a1.last_ping = self.now
        self.a1.n_pings = 1
        self.a1.status = "new"
        self.a1.save()

        self.a2 = Check(user=self.alice, name="Alice 2")
        self.a2.timeout = td(seconds=86400)
        self.a2.grace = td(seconds=3600)
        self.a2.last_ping = self.now
        self.a2.status = "up"
        self.a2.save()

    def get(self):
        return self.client.get("/api/v1/checks/", HTTP_X_API_KEY="abc")

    def test_it_works(self):
        r = self.get()
        self.assertEqual(r.status_code, 200)

        doc = r.json()
        self.assertTrue("checks" in doc)

        checks = {check["name"]: check for check in doc["checks"]}
        self.assertEqual(len(checks), 2)

        self.assertEqual(checks["Alice 1"]["timeout"], 3600)
        self.assertEqual(checks["Alice 1"]["grace"], 900)
        self.assertEqual(checks["Alice 1"]["ping_url"], self.a1.url())
        self.assertEqual(checks["Alice 1"]["last_ping"], self.now.isoformat())
        self.assertEqual(checks["Alice 1"]["n_pings"], 1)
        self.assertEqual(checks["Alice 1"]["status"], "new")
        pause_url = "{0}/api/v1/checks/%s/pause".format(getattr(settings, "SITE_ROOT")) % self.a1.code
        self.assertEqual(checks["Alice 1"]["pause_url"], pause_url)

        next_ping = self.now + td(seconds=3600)
        self.assertEqual(checks["Alice 1"]["next_ping"], next_ping.isoformat())

        self.assertEqual(checks["Alice 2"]["timeout"], 86400)
        self.assertEqual(checks["Alice 2"]["grace"], 3600)
        self.assertEqual(checks["Alice 2"]["ping_url"], self.a2.url())
        self.assertEqual(checks["Alice 2"]["status"], "up")

    def test_it_shows_only_users_checks(self):
        bobs_check = Check(user=self.bob, name="Bob 1")
        bobs_check.save()

        r = self.get()
        data = r.json()
        self.assertEqual(len(data["checks"]), 2)
        for check in data["checks"]:
            self.assertNotEqual(check["name"], "Bob 1")

    def test_it_accepts_api_key_from_request_body(self):
        payload = json.dumps({"api_key": "abc"})
        r = self.client.generic("GET", "/api/v1/checks/", payload,
                                content_type="application/json")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Alice")
