from datetime import timedelta as td
from datetime import datetime as dt
from datetime import timezone

from hc.api.models import Check, Flip
from hc.test import BaseTestCase


class GetFlipsTestCase(BaseTestCase):
    def setUp(self):
        super(GetFlipsTestCase, self).setUp()

        self.a1 = Check(project=self.project, name="Alice 1")
        self.a1.timeout = td(seconds=3600)
        self.a1.grace = td(seconds=900)
        self.a1.n_pings = 0
        self.a1.status = "new"
        self.a1.tags = "a1-tag a1-additional-tag"
        self.a1.desc = "This is description"
        self.a1.save()

        Flip.objects.create(
            owner=self.a1,
            created=dt(2020, 6, 1, 12, 24, 32, 123000, tzinfo=timezone.utc),
            old_status="new",
            new_status="up",
        )

        self.url = "/api/v1/checks/%s/flips/" % self.a1.code

    def get(self, api_key="X" * 32, qs=""):
        return self.client.get(self.url + qs, HTTP_X_API_KEY=api_key)

    def test_it_works(self):

        r = self.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        self.assertEqual(len(doc["flips"]), 1)

        flip = doc["flips"][0]
        # Microseconds (123000) should be stripped out
        self.assertEqual(flip["timestamp"], "2020-06-01T12:24:32+00:00")
        self.assertEqual(flip["up"], 1)

    def test_readonly_key_is_allowed(self):
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.get(api_key=self.project.api_key_readonly)
        self.assertEqual(r.status_code, 200)

    def test_it_rejects_post(self):
        r = self.client.post(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 405)

    def test_it_rejects_non_integer_start(self):
        r = self.get(qs="?start=abc")
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_negative_start(self):
        r = self.get(qs="?start=-123")
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_huge_start(self):
        r = self.get(qs="?start=12345678901234567890")
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_negative_seconds(self):
        r = self.get(qs="?seconds=-123")
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_huge_seconds(self):
        r = self.get(qs="?seconds=12345678901234567890")
        self.assertEqual(r.status_code, 400)
