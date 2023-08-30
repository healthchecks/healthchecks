from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class FilteringRulesTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        self.url = f"/checks/{self.check.code}/filtering_rules/"
        self.redirect_url = f"/checks/{self.check.code}/details/"

    def test_it_works(self) -> None:
        payload = {
            "filter_subject": "on",
            "filter_body": "on",
            "start_kw": "START",
            "success_kw": "SUCCESS",
            "failure_kw": "ERROR",
            "methods": "POST",
            "manual_resume": "1",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertTrue(self.check.filter_subject)
        self.assertTrue(self.check.filter_body)
        self.assertEqual(self.check.start_kw, "START")
        self.assertEqual(self.check.success_kw, "SUCCESS")
        self.assertEqual(self.check.failure_kw, "ERROR")
        self.assertEqual(self.check.methods, "POST")
        self.assertTrue(self.check.manual_resume)

    def test_it_clears_methods(self) -> None:
        self.check.methods = "POST"
        self.check.save()

        payload = {"methods": "", "filter_by_subject": "yes"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.methods, "")

    def test_it_clears_filtering_fields(self) -> None:
        self.check.filter_subject = True
        self.check.filter_body = True
        self.check.start_kw = "START"
        self.check.success_kw = "SUCCESS"
        self.check.failure_kw = "ERROR"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data={"methods": ""})
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertFalse(self.check.filter_subject)
        self.assertFalse(self.check.filter_body)
        self.assertEqual(self.check.start_kw, "")
        self.assertEqual(self.check.success_kw, "")
        self.assertEqual(self.check.failure_kw, "")

    def test_it_clears_manual_resume_flag(self) -> None:
        self.check.manual_resume = True
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data={"filter_by_subject": "no"})
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertFalse(self.check.manual_resume)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        payload = {
            "filter_subject": "on",
            "filter_body": "on",
            "success_kw": "SUCCESS",
            "failure_kw": "ERROR",
            "methods": "POST",
            "manual_resume": "1",
        }

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 403)
