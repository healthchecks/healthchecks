from __future__ import annotations

import json
from unittest.mock import Mock, patch

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(DISCORD_CLIENT_ID="t1", DISCORD_CLIENT_SECRET="s1")
class AddDiscordCompleteTestCase(BaseTestCase):
    url = "/integrations/add_discord/"

    @patch("hc.front.views.curl.post", autospec=True)
    def test_it_handles_oauth_response(self, mock_post: Mock) -> None:
        session = self.client.session
        session["add_discord"] = ("foo", str(self.project.code))
        session.save()

        oauth_response = {
            "access_token": "test-token",
            "webhook": {"url": "foo", "id": "bar"},
        }

        mock_post.return_value.text = json.dumps(oauth_response)
        mock_post.return_value.json.return_value = oauth_response

        url = self.url + "?code=12345678&state=foo"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "The Discord integration has been added!")

        ch = Channel.objects.get()
        self.assertEqual(ch.discord_webhook_url, "foo")
        self.assertEqual(ch.project, self.project)

        # Session should now be clean
        self.assertFalse("add_discord" in self.client.session)

    @patch("hc.front.views.curl.post", autospec=True)
    def test_it_handles_unexpected_oauth_response(self, mock_post: Mock) -> None:
        for sample in ("surprise", {}, None):
            oauth_response = "surprise"
            mock_post.return_value.text = json.dumps(oauth_response)
            mock_post.return_value.json.return_value = oauth_response

            session = self.client.session
            session["add_discord"] = ("foo", str(self.project.code))
            session.save()

            url = self.url + "?code=12345678&state=foo"

            self.client.login(username="alice@example.org", password="password")

            with patch("hc.front.views.logger") as logger:
                r = self.client.get(url, follow=True)
                self.assertRedirects(r, self.channels_url)
                self.assertContains(r, "Received an unexpected response from Discord.")
                self.assertTrue(logger.warning.called)

    def test_it_avoids_csrf(self) -> None:
        session = self.client.session
        session["add_discord"] = ("foo", str(self.project.code))
        session.save()

        url = self.url + "?code=12345678&state=bar"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

        # Session should now be clean
        self.assertFalse("add_discord" in self.client.session)

    def test_it_handles_access_denied(self) -> None:
        session = self.client.session
        session["add_discord"] = ("foo", str(self.project.code))
        session.save()

        url = self.url + "?error=access_denied"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "Discord setup was cancelled.")

        self.assertEqual(Channel.objects.count(), 0)

        # Session should now be clean
        self.assertFalse("add_discord" in self.client.session)

    @override_settings(DISCORD_CLIENT_ID=None)
    def test_it_requires_client_id(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?code=12345678&state=bar")
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self) -> None:
        session = self.client.session
        session["add_discord"] = ("foo", str(self.project.code))
        session.save()

        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url + "?code=12345678&state=foo")
        self.assertEqual(r.status_code, 403)
