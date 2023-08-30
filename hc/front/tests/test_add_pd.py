from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(PD_APP_ID=None)
class AddPdTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_pd/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Paste the Integration Key down below")

    def test_it_works(self) -> None:
        # Integration key is 32 characters long
        form = {"value": "12345678901234567890123456789012"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "pd")
        self.assertEqual(c.value, "12345678901234567890123456789012")

    def test_it_trims_whitespace(self) -> None:
        form = {"value": "   123456   "}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.value, "123456")

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(PD_ENABLED=False)
    def test_it_handles_disabled_integration(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    @override_settings(PD_APP_ID="FOOBAR")
    def test_it_handles_pd_app_id(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "app_id=FOOBAR")
        self.assertIn("pagerduty", self.client.session)
