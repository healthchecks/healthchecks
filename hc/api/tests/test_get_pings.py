from __future__ import annotations

from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from uuid import uuid4

from hc.api.models import Check, Ping
from hc.test import BaseTestCase, TestHttpResponse

EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)


class GetPingsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.a1 = Check(project=self.project, name="Alice 1")
        self.a1.timeout = td(seconds=3600)
        self.a1.grace = td(seconds=900)
        self.a1.n_pings = 1
        self.a1.status = "new"
        self.a1.tags = "a1-tag a1-additional-tag"
        self.a1.desc = "This is description"
        self.a1.save()

        self.ping = Ping(owner=self.a1)
        self.ping.n = 1
        self.ping.remote_addr = "1.2.3.4"
        self.ping.scheme = "https"
        self.ping.method = "get"
        self.ping.ua = "foo-agent"
        self.ping.save()

        self.url = "/api/v1/checks/%s/pings/" % self.a1.code

    def get(self, api_key: str = "X" * 32) -> TestHttpResponse:
        return self.csrf_client.get(self.url, HTTP_X_API_KEY=api_key)

    def test_it_works(self) -> None:
        r = self.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        self.assertEqual(len(doc["pings"]), 1)

        ping = doc["pings"][0]
        self.assertEqual(ping["n"], 1)
        self.assertEqual(ping["remote_addr"], "1.2.3.4")
        self.assertEqual(ping["scheme"], "https")
        self.assertEqual(ping["method"], "get")
        self.assertEqual(ping["ua"], "foo-agent")

    def test_readonly_key_is_not_allowed(self) -> None:
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.get(api_key=self.project.api_key_readonly)
        self.assertEqual(r.status_code, 401)

    def test_it_rejects_post(self) -> None:
        r = self.csrf_client.post(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 405)

    def test_it_handles_missing_api_key(self) -> None:
        r = self.client.get(self.url)
        self.assertContains(r, "missing api key", status_code=401)

    def test_it_calculates_overlapping_durations(self) -> None:
        self.ping.delete()

        m = td(minutes=1)
        a, b = uuid4(), uuid4()
        self.a1.ping_set.create(n=1, rid=a, created=EPOCH, kind="start")
        self.a1.ping_set.create(n=2, rid=b, created=EPOCH + m, kind="start")
        self.a1.ping_set.create(n=3, rid=a, created=EPOCH + m * 2)
        self.a1.ping_set.create(n=4, rid=b, created=EPOCH + m * 6)

        with self.assertNumQueries(4):
            doc = self.get().json()
            self.assertEqual(doc["pings"][0]["duration"], 300.0)
            self.assertEqual(doc["pings"][1]["duration"], 120.0)

    def test_it_disables_duration_calculation(self) -> None:
        self.ping.delete()
        # Set up a worst case scenario where each success ping has an unique rid,
        # and there are no "start" pings:
        for i in range(1, 12):
            self.a1.ping_set.create(n=i, rid=uuid4(), created=EPOCH + td(minutes=i))

        # Make sure we don't run Ping.duration() per ping:
        with self.assertNumQueries(4):
            doc = self.get().json()
            for d in doc["pings"]:
                self.assertNotIn("duration", d)

    def test_it_handles_rid(self) -> None:
        self.ping.rid = uuid4()
        self.ping.save()

        doc = self.get().json()
        ping = doc["pings"][0]
        self.assertEqual(ping["rid"], str(self.ping.rid))
