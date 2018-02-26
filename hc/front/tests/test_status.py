from hc.api.models import Check
from hc.test import BaseTestCase


class MyChecksTestCase(BaseTestCase):

    def setUp(self):
        super(MyChecksTestCase, self).setUp()
        self.check = Check(user=self.alice, name="Alice Was Here")
        self.check.tags = "foo"
        self.check.save()

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/status/")
        doc = r.json()

        self.assertEqual(doc["tags"]["foo"], "up")

        detail = doc["details"][0]
        self.assertEqual(detail["code"], str(self.check.code))
        self.assertEqual(detail["status"], "new")
        self.assertIn("Never", detail["last_ping"])
