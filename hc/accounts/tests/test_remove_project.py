from hc.api.models import Check
from hc.test import BaseTestCase


class RemoveProjectTestCase(BaseTestCase):
    def setUp(self):
        super(RemoveProjectTestCase, self).setUp()

        self.url = "/projects/%s/remove/" % self.project.code

    def test_it_works(self):
        Check.objects.create(project=self.project, tags="foo a-B_1  baz@")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, "/")

        # Alice's current project should be not set
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.current_project, None)

        # Alice should not own any projects
        self.assertFalse(self.alice.project_set.exists())

        # Check should be gone
        self.assertFalse(Check.objects.exists())

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_checks_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 404)
