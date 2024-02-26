from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Check
from hc.test import BaseTestCase


class BadgesTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.project.badge_key = "alices-badge-key"
        self.project.save()

        Check.objects.create(project=self.project, tags="foo a-B_1  baz@")

        self.url = f"/projects/{self.project.code}/badges/"

    def test_it_shows_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "foo")
        self.assertContains(r, "a-B_1")
        self.assertContains(r, self.project.badge_key)

    def test_it_checks_ownership(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_team_access_works(self) -> None:
        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    @override_settings(MASTER_BADGE_LABEL="Overall Status")
    def test_it_previews_master_svg(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        payload = {"target": "all", "fmt": "svg", "states": "2"}
        r = self.client.post(self.url, payload)

        self.assertContains(r, "![Overall Status]")

    def test_it_previews_svg(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        payload = {"target": "tag", "tag": "foo", "fmt": "svg", "states": "2"}
        r = self.client.post(self.url, payload)

        self.assertContains(r, "badge/alices-badge-key/")
        self.assertContains(r, "foo.svg")
        self.assertContains(r, "![foo]")

    def test_it_handles_special_characters_in_tags(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        payload = {"target": "tag", "tag": "db@dc1", "fmt": "svg", "states": "2"}
        r = self.client.post(self.url, payload)
        self.assertContains(r, "db%2540dc1.svg")
        self.assertContains(r, "![db@dc1]")

    def test_it_previews_json(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        payload = {"target": "tag", "tag": "foo", "fmt": "json", "states": "2"}
        r = self.client.post(self.url, payload)

        self.assertContains(r, "fetch-json")
        self.assertContains(r, "foo.json")
        self.assertNotContains(r, "![foo]")

    def test_it_previews_shields(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        payload = {"target": "tag", "tag": "foo", "fmt": "shields", "states": "2"}
        r = self.client.post(self.url, payload)

        self.assertContains(r, "https://img.shields.io/endpoint")
        self.assertContains(r, "%3A%2F%2F")  # url-encoded "://"
        self.assertContains(r, "foo.shields")
        self.assertContains(r, "![foo]")
