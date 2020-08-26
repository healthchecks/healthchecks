from hc.api.models import Check
from hc.test import BaseTestCase


class CopyCheckTestCase(BaseTestCase):
    def setUp(self):
        super(CopyCheckTestCase, self).setUp()
        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.subject = "success-keyword"
        self.check.subject_fail = "failure-keyword"
        self.check.methods = "POST"
        self.check.manual_resume = True
        self.check.save()

        self.copy_url = "/checks/%s/copy/" % self.check.code

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.copy_url, follow=True)
        self.assertContains(r, "This is a brand new check")

        copy = Check.objects.get(name="Foo (copy)")
        self.assertEqual(copy.subject, "success-keyword")
        self.assertEqual(copy.subject_fail, "failure-keyword")
        self.assertEqual(copy.methods, "POST")
        self.assertTrue(copy.manual_resume)

    def test_it_obeys_limit(self):
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.copy_url)
        self.assertEqual(r.status_code, 400)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.copy_url)
        self.assertEqual(r.status_code, 403)
