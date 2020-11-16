from hc.api.models import Check
from hc.test import BaseTestCase


class FilteringRulesTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        self.url = "/checks/%s/filtering_rules/" % self.check.code
        self.redirect_url = "/checks/%s/details/" % self.check.code

    def test_it_works(self):
        payload = {
            "subject": "SUCCESS",
            "subject_fail": "ERROR",
            "methods": "POST",
            "manual_resume": "1",
            "filter_by_subject": "yes",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.subject, "SUCCESS")
        self.assertEqual(self.check.subject_fail, "ERROR")
        self.assertEqual(self.check.methods, "POST")
        self.assertTrue(self.check.manual_resume)

    def test_it_clears_method(self):
        self.check.method = "POST"
        self.check.save()

        payload = {"subject": "SUCCESS", "methods": "", "filter_by_subject": "yes"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.methods, "")

    def test_it_clears_subject(self):
        self.check.subject = "SUCCESS"
        self.check.subject_fail = "ERROR"
        self.check.save()

        payload = {
            "methods": "",
            "filter_by_subject": "no",
            "subject": "foo",
            "subject_fail": "bar",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.subject, "")
        self.assertEqual(self.check.subject_fail, "")

    def test_it_clears_manual_resume_flag(self):
        self.check.manual_resume = True
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data={"filter_by_subject": "no"})
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertFalse(self.check.manual_resume)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        payload = {
            "subject": "SUCCESS",
            "subject_fail": "ERROR",
            "methods": "POST",
            "manual_resume": "1",
            "filter_by_subject": "yes",
        }

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 403)
