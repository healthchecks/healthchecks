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

        self.url = "/api/v1/checks/%s/flips/" % self.a1.code

    def get(self, api_key="X" * 32):
        return self.client.get(self.url, HTTP_X_API_KEY=api_key)

    def test_it_works(self):
        self.f1 = Flip(
            owner=self.a1,
            created=dt(2020,6,1,12,24,32,tzinfo=timezone.utc),
            old_status='new',
            new_status='up',
        )
        self.f1.save()

        r = self.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        self.assertEqual(len(doc["flips"]), 1)

        flip = doc["flips"][0]
        self.assertEqual(flip["timestamp"], dt(2020,6,1,12,24,32,tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        self.assertEqual(flip["up"], 1)

    def test_readonly_key_is_allowed(self):
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.get(api_key=self.project.api_key_readonly)
        self.assertEqual(r.status_code, 200)

    def test_it_rejects_post(self):
        r = self.client.post(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 405)
