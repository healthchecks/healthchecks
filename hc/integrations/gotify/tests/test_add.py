from __future__ import annotations

from hc.api.models import Channel
from hc.test import BaseTestCase


class AddGotifyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_gotify/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Gotify")

    def test_it_works(self) -> None:
        form = {"url": "http://example.org", "token": "abc"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "gotify")
        self.assertEqual(c.gotify.url, "http://example.org")
        self.assertEqual(c.gotify.token, "abc")
        self.assertEqual(c.project, self.project)

    def test_it_rejects_bad_url(self) -> None:
        form = {"url": "not an URL", "token": "abc"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Enter a valid URL")

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
