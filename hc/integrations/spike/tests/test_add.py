from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


class AddSpikeTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_spike/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Spike")

    def test_it_works(self) -> None:
        form = {"value": "http://example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "spike")
        self.assertEqual(c.value, "http://example.org")
        self.assertEqual(c.project, self.project)

    def test_it_rejects_bad_url(self) -> None:
        form = {"value": "not an URL"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Enter a valid URL")

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(SPIKE_ENABLED=False)
    def test_it_requires_spike_enabled(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
