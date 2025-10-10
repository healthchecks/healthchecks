from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


def _get_payload(**kwargs: str) -> dict[str, str]:
    payload = {
        "bot_email": "foo@example.org",
        "api_key": "fake-key",
        "site": "https://example.org",
        "mtype": "stream",
        "to": "general",
        "topic": "foo",
    }

    payload.update(kwargs)
    return payload


class AddZulipTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_zulip/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "open-source group chat app")

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, _get_payload())
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "zulip")
        self.assertEqual(c.zulip.bot_email, "foo@example.org")
        self.assertEqual(c.zulip.api_key, "fake-key")
        self.assertEqual(c.zulip.mtype, "stream")
        self.assertEqual(c.zulip.to, "general")
        self.assertEqual(c.zulip.site, "https://example.org")
        self.assertEqual(c.zulip.topic, "foo")

    def test_it_rejects_bad_email(self) -> None:
        payload = _get_payload(bot_email="not@an@email")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Invalid file format.")

    def test_it_rejects_missing_api_key(self) -> None:
        payload = _get_payload(api_key="")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Invalid file format.")

    def test_it_rejects_missing_site(self) -> None:
        payload = _get_payload(site="")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Invalid file format.")

    def test_it_rejects_malformed_site(self) -> None:
        payload = _get_payload(site="not an url")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Invalid file format.")

    def test_it_rejects_bad_mtype(self) -> None:
        payload = _get_payload(mtype="this-should-not-work")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 200)

    def test_it_rejects_missing_stream_name(self) -> None:
        payload = _get_payload(to="")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "This field is required.")

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(ZULIP_ENABLED=False)
    def test_it_handles_disabled_integration(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
