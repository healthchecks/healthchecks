from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class CopyCheckTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.slug = "custom-slug"
        self.check.filter_subject = True
        self.check.filter_body = True
        self.check.start_kw = "start-keyword"
        self.check.success_kw = "success-keyword"
        self.check.failure_kw = "failure-keyword"
        self.check.methods = "POST"
        self.check.manual_resume = True
        self.check.save()

        self.copy_url = f"/checks/{self.check.code}/copy/"

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.copy_url, follow=True)
        self.assertContains(r, "This is a brand new check")

        copy = Check.objects.get(name="Foo (copy)")
        self.assertEqual(copy.slug, "custom-slug-copy")
        self.assertTrue(copy.filter_subject)
        self.assertTrue(copy.filter_body)
        self.assertEqual(copy.start_kw, "start-keyword")
        self.assertEqual(copy.success_kw, "success-keyword")
        self.assertEqual(copy.failure_kw, "failure-keyword")
        self.assertEqual(copy.methods, "POST")
        self.assertTrue(copy.manual_resume)

    def test_it_obeys_limit(self) -> None:
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.copy_url)
        self.assertEqual(r.status_code, 400)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.copy_url)
        self.assertEqual(r.status_code, 403)

    def test_it_handles_long_check_name(self) -> None:
        self.check.name = "A" * 100
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.copy_url)

        q = Check.objects.filter(name="A" * 90 + "... (copy)")
        self.assertTrue(q.exists())
