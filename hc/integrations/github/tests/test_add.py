from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(GITHUB_CLIENT_ID="fake-client-id")
class AddGitHubTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_github/"

    def test_prompt_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "create an issue", status_code=200)
        self.assertContains(r, "github.com/login/oauth/authorize")

        self.assertTrue("add_github_state" in self.client.session)
        self.assertTrue("add_github_project" in self.client.session)

    @override_settings(GITHUB_CLIENT_ID=None)
    def test_it_requires_client_id(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
