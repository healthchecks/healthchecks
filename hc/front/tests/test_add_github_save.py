from __future__ import annotations

from unittest.mock import patch, Mock

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.lib.github import BadCredentials
from hc.test import BaseTestCase


@override_settings(GITHUB_CLIENT_ID="fake-client-id")
class AddGitHubSaveTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_github/save/"

        session = self.client.session
        session["add_github_project"] = "DEADBEEF"
        session["add_github_token"] = "CAFEBABE"
        session.save()

    @patch("hc.front.views.github", autospec=True)
    def test_it_works(self, github: Mock) -> None:
        github.get_repos.return_value = {"alice/foo": 123}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"repo_name": "alice/foo", "labels": "foo, bar"})
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "github")
        self.assertEqual(c.name, "alice/foo")
        self.assertEqual(c.github.installation_id, 123)
        self.assertEqual(c.github.repo, "alice/foo")
        self.assertEqual(c.github.labels, ["foo", "bar"])

        # It should clean up session
        session = self.client.session
        self.assertNotIn("add_github_project", session)
        self.assertNotIn("add_github_token", session)

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    @override_settings(GITHUB_CLIENT_ID=None)
    def test_it_requires_client_id(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"repo_name": "alice/foo"})
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, {"repo_name": "alice/foo"})
        self.assertEqual(r.status_code, 403)

    def test_it_handles_empty_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {})
        self.assertEqual(r.status_code, 400)

    @patch("hc.front.views.github", autospec=True)
    def test_it_handles_unexpected_repo_name(self, github: Mock) -> None:
        github.get_repos.return_value = {"alice/foo": 123}
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"repo_name": "alice/bar"})
        self.assertEqual(r.status_code, 403)

    @patch("hc.front.views.github.get_repos", Mock(side_effect=BadCredentials))
    def test_it_handles_bad_credentials(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"repo_name": "alice/bar"}, follow=True)

        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "GitHub setup failed, GitHub access was revoked.")

    def test_it_handles_no_session(self) -> None:
        session = self.client.session
        session.clear()
        session.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"repo_name": "alice/foo"})
        self.assertEqual(r.status_code, 403)
