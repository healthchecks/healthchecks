from __future__ import annotations

from json import dumps
from unittest.mock import Mock, patch

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(LINENOTIFY_CLIENT_ID="t1", LINENOTIFY_CLIENT_SECRET="s1")
class AddLineNotifyCompleteTestCase(BaseTestCase):
    url = "/integrations/add_linenotify/"

    @patch("hc.front.views.curl", autospec=True)
    def test_it_handles_oauth_response(self, mock_curl: Mock) -> None:
        session = self.client.session
        session["add_linenotify"] = ("foo", str(self.project.code))
        session.save()

        mock_curl.post.return_value.content = dumps(
            {"status": 200, "access_token": "test-token"}
        )

        mock_curl.get.return_value.content = dumps({"target": "Alice"})

        url = self.url + "?code=12345678&state=foo"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "The LINE Notify integration has been added!")

        ch = Channel.objects.get()
        self.assertEqual(ch.value, "test-token")
        self.assertEqual(ch.name, "Alice")
        self.assertEqual(ch.project, self.project)

        # Session should now be clean
        self.assertFalse("add_linenotify" in self.client.session)

    @patch("hc.front.views.curl", autospec=True)
    def test_it_handles_unexpected_token_response(self, mock_curl: Mock) -> None:
        mock_curl.get.return_value.content = dumps({"target": "Alice"})
        for sample in ("surprise", "{}", """{"status": 400, "access_token": "x"}"""):
            mock_curl.post.return_value.content = sample

            session = self.client.session
            session["add_linenotify"] = ("foo", str(self.project.code))
            session.save()

            url = self.url + "?code=12345678&state=foo"
            self.client.login(username="alice@example.org", password="password")

            with patch("hc.front.views.logger") as logger:
                r = self.client.get(url, follow=True)
                self.assertRedirects(r, self.channels_url)
                self.assertContains(
                    r, "Received an unexpected response from LINE Notify"
                )
                self.assertTrue(logger.warning.called)

    @patch("hc.front.views.curl", autospec=True)
    def test_it_handles_unexpected_status_response(self, mock_curl: Mock) -> None:
        mock_curl.post.return_value.content = dumps(
            {"status": 200, "access_token": "test-token"}
        )
        for sample in ("surprise", "{}", """{"target": 123}"""):
            mock_curl.get.return_value.content = sample

            session = self.client.session
            session["add_linenotify"] = ("foo", str(self.project.code))
            session.save()

            url = self.url + "?code=12345678&state=foo"
            self.client.login(username="alice@example.org", password="password")

            with patch("hc.front.views.logger") as logger:
                r = self.client.get(url, follow=True)
                self.assertRedirects(r, self.channels_url)
                self.assertContains(
                    r, "Received an unexpected response from LINE Notify"
                )
                self.assertTrue(logger.warning.called)

    def test_it_avoids_csrf(self) -> None:
        session = self.client.session
        session["add_linenotify"] = ("foo", str(self.project.code))
        session.save()

        url = self.url + "?code=12345678&state=bar"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

    def test_it_handles_denial(self) -> None:
        session = self.client.session
        session["add_linenotify"] = ("foo", str(self.project.code))
        session.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?error=access_denied&state=foo", follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "LINE Notify setup was cancelled")

        self.assertEqual(Channel.objects.count(), 0)

        # Session should now be clean
        self.assertFalse("add_linenotify" in self.client.session)

    @override_settings(LINENOTIFY_CLIENT_ID=None)
    def test_it_requires_client_id(self) -> None:
        url = self.url + "?code=12345678&state=bar"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self) -> None:
        session = self.client.session
        session["add_linenotify"] = ("foo", str(self.project.code))
        session.save()

        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        url = self.url + "?code=12345678&state=foo"
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)
