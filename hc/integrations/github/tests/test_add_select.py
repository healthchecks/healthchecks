from __future__ import annotations

from unittest.mock import Mock, patch

from django.test.utils import override_settings
from hc.integrations.github.client import BadCredentials
from hc.test import BaseTestCase


@override_settings(GITHUB_CLIENT_ID="fake-client-id")
@override_settings(GITHUB_PUBLIC_LINK="http://example.org")
class AddGitHubSelectTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = "/integrations/add_github/"

    @patch("hc.integrations.github.views.client", autospec=True)
    def test_it_works(self, client: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_state"] = "test-state"
        session.save()

        client.get_user_access_token.return_value = "test-token"
        client.get_repos.return_value = {"alice/foo": 123}
        r = self.client.get(self.url + "?state=test-state&code=test-code")

        get_token_args, _ = client.get_user_access_token.call_args
        self.assertEqual(get_token_args[0], "test-code")
        get_repos_args, _ = client.get_repos.call_args
        self.assertEqual(get_repos_args[0], "test-token")

        self.assertContains(r, "Save Integration", status_code=200)
        self.assertContains(r, "alice/foo")
        self.assertContains(r, f"/projects/{self.project.code}/add_github/save/")
        self.assertContains(r, "http://example.org/installations/new")

        self.assertEqual(self.client.session["add_github_token"], "test-token")

    @patch("hc.integrations.github.views.client", autospec=True)
    def test_it_skips_oauth_code_exchange(self, client: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_token"] = "test-token"
        session.save()

        client.get_repos.return_value = {"alice/foo": 123}
        r = self.client.get(self.url + "?state=test-state&code=test-code")

        self.assertFalse(client.get_user_access_token.called)
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

    @patch("hc.integrations.github.views.client", autospec=True)
    def test_it_handles_wrong_state(self, client: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_state"] = "test-state"
        session.save()

        r = self.client.get(self.url + "?state=wrong-state&code=test-code")
        self.assertEqual(r.status_code, 403)

    @patch("hc.integrations.github.views.client", autospec=True)
    def test_it_redirects_to_install_page(self, client: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_token"] = "test-token"
        session.save()

        client.get_repos.return_value = {}
        r = self.client.get(self.url + "?state=test-state&code=test-code")
        self.assertRedirects(
            r, "http://example.org/installations/new", fetch_redirect_response=False
        )

    def test_it_handles_access_denied(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_state"] = "test-state"
        session.save()

        r = self.client.get(
            self.url + "?error=access_denied&state=test-state", follow=True
        )
        self.assertRedirects(r, self.channels_url)

        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "GitHub setup was cancelled.")

    def test_it_handles_missing_code(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_state"] = "test-state"
        session.save()

        r = self.client.get(self.url + "?state=test-state")
        self.assertEqual(r.status_code, 400)

    @patch(
        "hc.integrations.github.views.client.get_repos",
        Mock(side_effect=BadCredentials),
    )
    def test_it_handles_bad_credentials(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["add_github_project"] = str(self.project.code)
        session["add_github_token"] = "test-token"
        session.save()

        r = self.client.get(self.url + "?state=test-state&code=test-code", follow=True)

        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "GitHub setup failed, GitHub access was revoked.")

        # It should clean up session
        session = self.client.session
        self.assertNotIn("add_github_project", session)
        self.assertNotIn("add_github_token", session)
