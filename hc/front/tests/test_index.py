from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class IndexTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.c1 = Check.objects.create(project=self.project)
        self.c2 = Check.objects.create(project=self.project)
        self.c3 = Check.objects.create(project=self.project)

    def test_it_shows_projects(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/")

        self.assertContains(r, "Alices Project")
        self.assertContains(r, "3 checks")
        self.assertContains(r, "status ic-up")

    def test_it_shows_overall_down_status(self):
        self.c1.status = "down"
        self.c1.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/")
        self.assertContains(r, "status ic-down")
