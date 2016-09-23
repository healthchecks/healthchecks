import json

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class CreateCheckTestCase(BaseTestCase):
    URL = "/api/v1/checks/"

    def post(self, data, expected_error=None, expected_fragment=None):
        r = self.client.post(self.URL, json.dumps(data),
                             content_type="application/json")

        if expected_error:
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json()["error"], expected_error)

        if expected_fragment:
            self.assertEqual(r.status_code, 400)
            self.assertIn(expected_fragment, r.json()["error"])

        return r

    def test_it_works(self):
        r = self.post({
            "api_key": "abc",
            "name": "Foo",
            "tags": "bar,baz",
            "timeout": 3600,
            "grace": 60
        })

        self.assertEqual(r.status_code, 201)

        doc = r.json()
        assert "ping_url" in doc
        self.assertEqual(doc["name"], "Foo")
        self.assertEqual(doc["tags"], "bar,baz")
        self.assertEqual(doc["last_ping"], None)
        self.assertEqual(doc["n_pings"], 0)

        self.assertEqual(Check.objects.count(), 1)
        check = Check.objects.get()
        self.assertEqual(check.name, "Foo")
        self.assertEqual(check.tags, "bar,baz")
        self.assertEqual(check.timeout.total_seconds(), 3600)
        self.assertEqual(check.grace.total_seconds(), 60)

    def test_it_accepts_api_key_in_header(self):
        payload = json.dumps({"name": "Foo"})
        r = self.client.post(self.URL, payload,
                             content_type="application/json",
                             HTTP_X_API_KEY="abc")

        self.assertEqual(r.status_code, 201)

    def test_it_assigns_channels(self):
        channel = Channel(user=self.alice)
        channel.save()

        r = self.post({"api_key": "abc", "channels": "*"})

        self.assertEqual(r.status_code, 201)
        check = Check.objects.get()
        self.assertEqual(check.channel_set.get(), channel)

    def test_it_supports_unique(self):
        existing = Check(user=self.alice, name="Foo")
        existing.save()

        r = self.post({
            "api_key": "abc",
            "name": "Foo",
            "unique": ["name"]
        })

        # Expect 200 instead of 201
        self.assertEqual(r.status_code, 200)

        # And there should be only one check in the database:
        self.assertEqual(Check.objects.count(), 1)

    def test_it_handles_missing_request_body(self):
        r = self.client.post(self.URL, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "wrong api_key")

    def test_it_handles_invalid_json(self):
        r = self.client.post(self.URL, "this is not json",
                             content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "could not parse request body")

    def test_it_rejects_wrong_api_key(self):
        self.post({"api_key": "wrong"},
                  expected_error="wrong api_key")

    def test_it_rejects_small_timeout(self):
        self.post({"api_key": "abc", "timeout": 0},
                  expected_fragment="timeout is too small")

    def test_it_rejects_large_timeout(self):
        self.post({"api_key": "abc", "timeout": 604801},
                  expected_fragment="timeout is too large")

    def test_it_rejects_non_number_timeout(self):
        self.post({"api_key": "abc", "timeout": "oops"},
                  expected_fragment="timeout is not a number")

    def test_it_rejects_non_string_name(self):
        self.post({"api_key": "abc", "name": False},
                  expected_fragment="name is not a string")

    def test_unique_accepts_only_whitelisted_values(self):
        existing = Check(user=self.alice, name="Foo")
        existing.save()

        self.post({
            "api_key": "abc",
            "name": "Foo",
            "unique": ["status"]
        }, expected_fragment="unexpected value")

    def test_it_rejects_bad_unique_values(self):
        self.post({
            "api_key": "abc",
            "name": "Foo",
            "unique": "not a list"
        }, expected_fragment="not an array")
