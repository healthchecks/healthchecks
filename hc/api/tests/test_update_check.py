import json

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class UpdateCheckTestCase(BaseTestCase):

    def setUp(self):
        super(UpdateCheckTestCase, self).setUp()
        self.check = Check(user=self.alice)
        self.check.save()

    def post(self, code, data):
        url = "/api/v1/checks/%s" % code
        r = self.client.post(url, json.dumps(data),
                             content_type="application/json")

        return r

    def test_it_works(self):
        r = self.post(self.check.code, {
            "api_key": "abc",
            "name": "Foo",
            "tags": "bar,baz",
            "timeout": 3600,
            "grace": 60
        })

        self.assertEqual(r.status_code, 200)

        doc = r.json()
        assert "ping_url" in doc
        self.assertEqual(doc["name"], "Foo")
        self.assertEqual(doc["tags"], "bar,baz")
        self.assertEqual(doc["last_ping"], None)
        self.assertEqual(doc["n_pings"], 0)

        self.assertTrue("schedule" not in doc)
        self.assertTrue("tz" not in doc)

        self.assertEqual(Check.objects.count(), 1)

        self.check.refresh_from_db()
        self.assertEqual(self.check.name, "Foo")
        self.assertEqual(self.check.tags, "bar,baz")
        self.assertEqual(self.check.timeout.total_seconds(), 3600)
        self.assertEqual(self.check.grace.total_seconds(), 60)

    def test_it_unassigns_channels(self):
        channel = Channel(user=self.alice)
        channel.save()

        self.check.assign_all_channels()

        r = self.post(self.check.code, {
            "api_key": "abc",
            "channels": ""
        })

        self.assertEqual(r.status_code, 200)
        check = Check.objects.get()
        self.assertEqual(check.channel_set.count(), 0)

    def test_it_requires_post(self):
        url = "/api/v1/checks/%s" % self.check.code
        r = self.client.get(url, HTTP_X_API_KEY="abc")
        self.assertEqual(r.status_code, 405)

    def test_it_handles_invalid_uuid(self):
        r = self.post("not-an-uuid", {"api_key": "abc"})
        self.assertEqual(r.status_code, 400)

    def test_it_handles_missing_check(self):
        made_up_code = "07c2f548-9850-4b27-af5d-6c9dc157ec02"
        r = self.post(made_up_code, {"api_key": "abc"})
        self.assertEqual(r.status_code, 404)

    def test_it_validates_ownership(self):
        check = Check(user=self.bob, status="up")
        check.save()

        r = self.post(check.code, {"api_key": "abc"})
        self.assertEqual(r.status_code, 403)

    def test_it_updates_cron_to_simple(self):
        self.check.kind = "cron"
        self.check.schedule = "5 * * * *"
        self.check.save()

        r = self.post(self.check.code, {"api_key": "abc", "timeout": 3600})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")
