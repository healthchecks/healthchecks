from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class AddCheckTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.url = f"/projects/{self.project.code}/checks/add/"
        self.redirect_url = f"/projects/{self.project.code}/checks/"

    def _payload(self, **kwargs: str) -> dict[str, str]:
        payload = {
            "name": "Test",
            "slug": "custom-slug",
            "tags": "foo bar",
            "kind": "simple",
            "timeout": "120",
            "grace": "60",
            "tz": "Europe/Riga",
        }
        payload.update(kwargs)
        return payload

    def test_it_works(self) -> None:
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

    def test_redirect_preserves_querystring(self) -> None:
        referer = self.redirect_url + "?tag=foo"
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(), HTTP_REFERER=referer)
        self.assertRedirects(r, referer)

    def test_it_saves_cron_schedule(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(kind="cron", schedule="0 0 * * *"))

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)
        self.assertEqual(check.kind, "cron")
        self.assertEqual(check.schedule, "0 0 * * *")

        self.assertRedirects(r, self.redirect_url)

    def test_it_saves_oncalendar_schedule(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        payload = self._payload(kind="oncalendar", schedule="12:34")
        r = self.client.post(self.url, payload)

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)
        self.assertEqual(check.kind, "oncalendar")
        self.assertEqual(check.schedule, "12:34")

        self.assertRedirects(r, self.redirect_url)

    def test_it_sanitizes_tags(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(tags="   foo  bar "))

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)
        self.assertEqual(check.tags, "foo bar")

        self.assertRedirects(r, self.redirect_url)

    def test_it_validates_kind(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(kind="surprise"))
        self.assertEqual(r.status_code, 400)

    def test_it_validates_timeout(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        for timeout in ["1", "31536001", "a"]:
            r = self.client.post(self.url, self._payload(timeout=timeout))
            self.assertEqual(r.status_code, 400)

    def test_it_validates_cron_expression(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(kind="cron", schedule="* * *"))
        self.assertEqual(r.status_code, 400)

    def test_it_validates_cron_expression_with_no_matches(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(
            self.url, self._payload(kind="cron", schedule="* * */100 * MON#2")
        )
        self.assertEqual(r.status_code, 400)

    def test_it_validates_oncalendar_expression(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(
            self.url, self._payload(kind="oncalendar", schedule="12:345")
        )
        self.assertEqual(r.status_code, 400)

    def test_it_validates_tz(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload(tz="Etc/Surprise"))
        self.assertEqual(r.status_code, 400)

    def test_team_access_works(self) -> None:
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, self._payload())

        check = Check.objects.get()
        # Added by bob, but should belong to alice (bob has team access)
        self.assertEqual(check.project, self.project)

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, self._payload())
        self.assertEqual(r.status_code, 403)

    def test_it_obeys_check_limit(self) -> None:
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, self._payload())
        self.assertEqual(r.status_code, 400)
