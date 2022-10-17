from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


class AddPrometheusTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = "/projects/%s/add_prometheus/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Prometheus")
        self.assertContains(r, f"{self.project.code}/metrics/")

    @override_settings(PROMETHEUS_ENABLED=False)
    def test_it_handles_disabled_integration(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
