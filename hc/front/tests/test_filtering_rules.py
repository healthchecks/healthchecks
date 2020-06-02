from hc.api.models import Check
from hc.test import BaseTestCase


class FilteringRulesTestCase(BaseTestCase):
    def setUp(self):
        super(FilteringRulesTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project)

        self.url = "/checks/%s/filtering_rules/" % self.check.code
        self.redirect_url = "/checks/%s/details/" % self.check.code

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(
            self.url,
            data={"subject": "SUCCESS", "methods": "POST", "manual_resume": "1"},
        )
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.subject, "SUCCESS")
        self.assertEqual(self.check.methods, "POST")
        self.assertTrue(self.check.manual_resume)

    def test_it_clears_method(self):
        self.check.method = "POST"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data={"subject": "SUCCESS", "methods": ""})
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.methods, "")

    def test_it_clears_subject(self):
        self.check.subject = "SUCCESS"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data={"methods": ""})
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.subject, "")

    def test_it_clears_manual_resume_flag(self):
        self.check.manual_resume = True
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data={})
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertFalse(self.check.manual_resume)
