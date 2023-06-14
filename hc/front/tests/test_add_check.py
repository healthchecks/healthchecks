from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class AddCheckTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.url = "/projects/%s/checks/add/" % self.project.code
        self.redirect_url = "/projects/%s/checks/" % self.project.code

    def _payload(self, **kwargs):
        payload = {
            "name": "Test",
            "slug": "custom-slug",
            "tags": "foo bar",
            "kind": "simple",
            "timeout": "120",
            "grace": "60",
            "schedule": "* * * * *",
            "tz": "Europe/Riga",
        }
        payload.update(kwargs)
        return payload

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload())

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)
        self.assertEqual(check.name, "Test")
        self.assertEqual(check.slug, "custom-slug")
        self.assertEqual(check.tags, "foo bar")
        self.assertEqual(check.kind, "simple")
        self.assertEqual(check.timeout.total_seconds(), 120)
        self.assertEqual(check.grace.total_seconds(), 60)
        self.assertEqual(check.schedule, "* * * * *")
        self.assertEqual(check.tz, "Europe/Riga")

        self.assertRedirects(r, self.redirect_url)

    def test_redirect_preserves_querystring(self):
        referer = self.redirect_url + "?tag=foo"
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(), HTTP_REFERER=referer)
        self.assertRedirects(r, referer)

    def test_it_saves_cron_schedule(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(kind="cron"))

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)
        self.assertEqual(check.kind, "cron")

        self.assertRedirects(r, self.redirect_url)

    def test_it_sanitizes_tags(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(tags="   foo  bar "))

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)
        self.assertEqual(check.tags, "foo bar")

        self.assertRedirects(r, self.redirect_url)

    def test_it_validates_kind(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(kind="surprise"))
        self.assertEqual(r.status_code, 400)

    def test_it_validates_timeout(self):
        self.client.login(username="alice@example.org", password="password")
        for timeout in ["1", "31536001", "a"]:
            r = self.client.post(self.url, self._payload(timeout=timeout))
            self.assertEqual(r.status_code, 400)

    def test_it_validates_cron_expression(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(schedule="* * *"))
        self.assertEqual(r.status_code, 400)

    def test_it_validates_cron_expression_with_no_matches(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(schedule="* * */100 * MON#2"))
        self.assertEqual(r.status_code, 400)

    def test_it_validates_tz(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(tz="Etc/Surprise"))
        self.assertEqual(r.status_code, 400)

    def test_team_access_works(self):
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, self._payload())

        check = Check.objects.get()
        # Added by bob, but should belong to alice (bob has team access)
        self.assertEqual(check.project, self.project)

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_requires_rw_access(self):
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, self._payload())
        self.assertEqual(r.status_code, 403)

    def test_it_obeys_check_limit(self):
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload())
        self.assertEqual(r.status_code, 400)
