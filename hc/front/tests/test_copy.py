from hc.api.models import Check
from hc.test import BaseTestCase


class CopyCheckTestCase(BaseTestCase):
    def setUp(self):
        super(CopyCheckTestCase, self).setUp()
        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.save()

        self.copy_url = "/checks/%s/copy/" % self.check.code

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.copy_url, follow=True)
        self.assertContains(r, "This is a brand new check")
        self.assertContains(r, "Foo (copy)")

    def test_it_obeys_limit(self):
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.copy_url)
        self.assertEqual(r.status_code, 400)
