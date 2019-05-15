from hc.api.models import Check
from hc.test import BaseTestCase


class MyChecksTestCase(BaseTestCase):
    def setUp(self):
        super(MyChecksTestCase, self).setUp()
        self.check = Check(project=self.project, name="Alice Was Here")
        self.check.tags = "foo"
        self.check.save()

        self.url = "/projects/%s/checks/status/" % self.project.code

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        doc = r.json()

        self.assertEqual(doc["tags"]["foo"], "up")

        detail = doc["details"][0]
        self.assertEqual(detail["code"], str(self.check.code))
        self.assertEqual(detail["status"], "new")
        self.assertIn("Never", detail["last_ping"])

    def test_it_allows_cross_team_access(self):
        self.bobs_profile.current_project = None
        self.bobs_profile.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_checks_ownership(self):
        self.bobs_profile.current_project = None
        self.bobs_profile.save()

        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
