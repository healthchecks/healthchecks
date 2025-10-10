from __future__ import annotations

import json

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


class AddOpsgenieTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_opsgenie/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "escalation policies, and incident tracking")

    def test_it_works(self) -> None:
        form = {"key": "123456", "region": "us"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "opsgenie")

        payload = json.loads(c.value)
        self.assertEqual(payload["key"], "123456")
        self.assertEqual(payload["region"], "us")
        self.assertEqual(c.project, self.project)

    def test_it_trims_whitespace(self) -> None:
        form = {"key": "   123456   ", "region": "us"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        payload = json.loads(c.value)
        self.assertEqual(payload["key"], "123456")

    def test_it_saves_eu_region(self) -> None:
        form = {"key": "123456", "region": "eu"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        payload = json.loads(c.value)
        self.assertEqual(payload["region"], "eu")

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(OPSGENIE_ENABLED=False)
    def test_it_handles_disabled_integration(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
