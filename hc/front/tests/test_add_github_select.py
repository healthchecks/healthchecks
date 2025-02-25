from __future__ import annotations

from unittest.mock import patch, Mock

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(GITHUB_CLIENT_ID="fake-client-id")
@override_settings(GITHUB_PUBLIC_LINK="http://example.org")
class AddGitHubSelectTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = "/integrations/add_github/"

    @patch("hc.front.views.github", autospec=True)
    def test_it_works(self, github: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_state"] = "test-state"
        session.save()

        github.get_user_access_token.return_value = "test-token"
        github.get_repos.return_value = {"alice/foo": 123}
        r = self.client.get(self.url + "?state=test-state&code=test-code")

        get_token_args, _ = github.get_user_access_token.call_args
        self.assertEqual(get_token_args[0], "test-code")
        get_repos_args, _ = github.get_repos.call_args
        self.assertEqual(get_repos_args[0], "test-token")

        self.assertContains(r, "Save Integration", status_code=200)
        self.assertContains(r, "alice/foo")
        self.assertContains(r, f"/projects/{self.project.code}/add_github/save/")
        self.assertContains(r, "http://example.org/installations/new")

        self.assertEqual(self.client.session["add_github_token"], "test-token")
        self.assertEqual(self.client.session["add_github_repos"], {"alice/foo": 123})

    @patch("hc.front.views.github", autospec=True)
    def test_it_skips_oauth_code_exchange(self, github: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_token"] = "test-token"
        session.save()

        github.get_repos.return_value = {"alice/foo": 123}
        r = self.client.get(self.url + "?state=test-state&code=test-code")

        self.assertFalse(github.get_user_access_token.called)
        self.assertContains(r, "alice/foo")

    @override_settings(GITHUB_CLIENT_ID=None)
    def test_it_requires_client_id(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_token"] = "test-token"
        session.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_handles_no_session(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?state=test-state&code=test-code")
        self.assertEqual(r.status_code, 403)

    def test_it_handles_no_state_and_no_token(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session.save()

        r = self.client.get(self.url + "?state=test-state&code=test-code")
        self.assertEqual(r.status_code, 403)

    @patch("hc.front.views.github", autospec=True)
    def test_it_handles_wrong_state(self, github: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_state"] = "test-state"
        session.save()

        r = self.client.get(self.url + "?state=wrong-state&code=test-code")
        self.assertEqual(r.status_code, 403)

    @patch("hc.front.views.github", autospec=True)
    def test_it_redirects_to_install_page(self, github: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_token"] = "test-token"
        session.save()

        github.get_repos.return_value = {}
        r = self.client.get(self.url + "?state=test-state&code=test-code")
        self.assertRedirects(
            r, "http://example.org/installations/new", fetch_redirect_response=False
        )
