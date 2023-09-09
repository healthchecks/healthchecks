from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(TWILIO_ACCOUNT="foo", TWILIO_AUTH="foo", TWILIO_FROM="123")
class AddCallTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_call/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Get a phone call")

    @override_settings(USE_PAYMENTS=True)
    def test_it_warns_about_limits(self) -> None:
        self.profile.sms_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "upgrade to a")

    def test_it_creates_channel(self) -> None:
        form = {"label": "My Phone", "phone": "+1234567890"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "call")
        self.assertEqual(c.phone.value, "+1234567890")
        self.assertEqual(c.name, "My Phone")
        self.assertEqual(c.project, self.project)

    def test_it_rejects_bad_number(self) -> None:
        form = {"phone": "not a phone number"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Invalid phone number format.")

    def test_it_trims_whitespace(self) -> None:
        form = {"phone": "   +1234567890   "}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.phone.value, "+1234567890")

    @override_settings(TWILIO_AUTH=None)
    def test_it_requires_credentials(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
