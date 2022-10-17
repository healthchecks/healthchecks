from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class BadgesTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.url = "/projects/%s/badges/" % self.project.code

    def test_it_shows_badges(self):
        Check.objects.create(project=self.project, tags="foo a-B_1  baz@")
        Check.objects.create(project=self.bobs_project, tags="bobs-tag")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "foo.svg")
        self.assertContains(r, "a-B_1.svg")

        # Expect badge URLs only for tags that match \w+
        self.assertNotContains(r, "baz@.svg")

        # Expect only Alice's tags
        self.assertNotContains(r, "bobs-tag.svg")

    def test_it_uses_badge_key(self):
        Check.objects.create(project=self.project, tags="foo bar")
        Check.objects.create(project=self.bobs_project, tags="bobs-tag")

        self.project.badge_key = "alices-badge-key"
        self.project.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "badge/alices-badge-key/")
        self.assertContains(r, "badge/alices-badge-key/")

    def test_it_handles_special_characers_in_tags(self):
        Check.objects.create(project=self.project, tags="db@dc1")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "db%2540dc1.svg")
