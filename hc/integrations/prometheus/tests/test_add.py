from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


class AddPrometheusTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_prometheus/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Prometheus")
        self.assertContains(r, f"{self.project.code}/metrics/")

    @override_settings(PROMETHEUS_ENABLED=False)
    def test_it_handles_disabled_integration(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
