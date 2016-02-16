import json

from hc.api.models import Check
from hc.test import BaseTestCase
from hc.accounts.models import Profile


class CreateCheckTestCase(BaseTestCase):

    def setUp(self):
        super(CreateCheckTestCase, self).setUp()
        self.profile = Profile(user=self.alice, api_key="abc")
        self.profile.save()

    def post(self, url, data):
        return self.client.post(url, json.dumps(data),
                                content_type="application/json")

    def test_it_works(self):
        r = self.post("/api/v1/checks/", {
            "api_key": "abc",
            "name": "Foo",
            "tags": "bar,baz",
            "timeout": 3600,
            "grace": 60
        })

        self.assertEqual(r.status_code, 201)
        self.assertTrue("ping_url" in r.json())

        self.assertEqual(Check.objects.count(), 1)
        check = Check.objects.get()
        self.assertEqual(check.name, "Foo")
        self.assertEqual(check.tags, "bar,baz")
        self.assertEqual(check.timeout.total_seconds(), 3600)
        self.assertEqual(check.grace.total_seconds(), 60)

    def test_it_handles_missing_request_body(self):
        r = self.client.post("/api/v1/checks/",
                             content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "wrong api_key")

    def test_it_rejects_wrong_api_key(self):
        r = self.post("/api/v1/checks/", {"api_key": "wrong"})
        self.assertEqual(r.json()["error"], "wrong api_key")

    def test_it_handles_invalid_json(self):
        r = self.client.post("/api/v1/checks/", "this is not json",
                             content_type="application/json")
        self.assertEqual(r.json()["error"], "could not parse request body")

    def test_it_reject_small_timeout(self):
        r = self.post("/api/v1/checks/", {"api_key": "abc", "timeout": 0})
        self.assertEqual(r.json()["error"], "timeout is too small")

    def test_it_rejects_large_timeout(self):
        r = self.post("/api/v1/checks/", {"api_key": "abc", "timeout": 604801})
        self.assertEqual(r.json()["error"], "timeout is too large")

    def test_it_rejects_non_number_timeout(self):
        r = self.post("/api/v1/checks/", {"api_key": "abc", "timeout": "oops"})
        self.assertEqual(r.json()["error"], "timeout is not a number")

    def test_it_rejects_non_string_name(self):
        r = self.post("/api/v1/checks/", {"api_key": "abc", "name": False})
        self.assertEqual(r.json()["error"], "name is not a string")
