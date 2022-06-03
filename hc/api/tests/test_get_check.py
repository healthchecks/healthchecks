from datetime import timedelta as td

from django.utils.timezone import now
from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class GetCheckTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.now = now().replace(microsecond=0)

        self.a1 = Check(project=self.project)
        self.a1.set_name_slug("Alice 1")
        self.a1.timeout = td(seconds=3600)
        self.a1.grace = td(seconds=900)
        self.a1.n_pings = 0
        self.a1.status = "new"
        self.a1.tags = "a1-tag a1-additional-tag"
        self.a1.desc = "This is description"
        self.a1.subject = "SUCCESS"
        self.a1.subject_fail = "ERROR"
        self.a1.save()

        self.c1 = Channel.objects.create(project=self.project)
        self.a1.channel_set.add(self.c1)

    def get(self, code, api_key="X" * 32):
        url = "/api/v1/checks/%s" % code
        return self.client.get(url, HTTP_X_API_KEY=api_key)

    def test_it_works(self):
        r = self.get(self.a1.code)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        self.assertEqual(len(doc), 18)

        self.assertEqual(doc["slug"], "alice-1")
        self.assertEqual(doc["timeout"], 3600)
        self.assertEqual(doc["grace"], 900)
        self.assertEqual(doc["ping_url"], self.a1.url())
        self.assertEqual(doc["last_ping"], None)
        self.assertEqual(doc["n_pings"], 0)
        self.assertEqual(doc["status"], "new")
        self.assertEqual(doc["channels"], str(self.c1.code))
        self.assertEqual(doc["desc"], "This is description")
        self.assertFalse(doc["manual_resume"])
        self.assertEqual(doc["methods"], "")
        self.assertEqual(doc["subject"], "SUCCESS")
        self.assertEqual(doc["subject_fail"], "ERROR")

    def test_it_handles_invalid_uuid(self):
        r = self.get("not-an-uuid")
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_check(self):
        made_up_code = "07c2f548-9850-4b27-af5d-6c9dc157ec02"
        r = self.get(made_up_code)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_unique_key(self):
        r = self.get(self.a1.unique_key)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        self.assertEqual(len(doc), 18)

        self.assertEqual(doc["timeout"], 3600)
        self.assertEqual(doc["grace"], 900)
        self.assertEqual(doc["ping_url"], self.a1.url())
        self.assertEqual(doc["last_ping"], None)
        self.assertEqual(doc["n_pings"], 0)
        self.assertEqual(doc["status"], "new")
        self.assertEqual(doc["channels"], str(self.c1.code))
        self.assertEqual(doc["desc"], "This is description")

    def test_it_rejects_post_unique_key(self):
        r = self.csrf_client.post(f"/api/v1/checks/{self.a1.unique_key}")
        self.assertEqual(r.status_code, 405)

    def test_readonly_key_works(self):
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.get(self.a1.code, api_key=self.project.api_key_readonly)
        self.assertEqual(r.status_code, 200)

        # When using readonly keys, the ping URLs should not be exposed:
        self.assertNotContains(r, self.a1.url())
