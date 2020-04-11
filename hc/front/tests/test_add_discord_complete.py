import json
from unittest.mock import patch

from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(DISCORD_CLIENT_ID="t1", DISCORD_CLIENT_SECRET="s1")
class AddDiscordCompleteTestCase(BaseTestCase):
    url = "/integrations/add_discord/"

    @patch("hc.front.views.requests.post")
    def test_it_handles_oauth_response(self, mock_post):
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

    def test_it_avoids_csrf(self):
        session = self.client.session
        session["add_discord"] = ("foo", str(self.project.code))
        session.save()

        url = self.url + "?code=12345678&state=bar"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

        # Session should now be clean
        self.assertFalse("add_discord" in self.client.session)

    def test_it_handles_access_denied(self):
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
    def test_it_requires_client_id(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?code=12345678&state=bar")
        self.assertEqual(r.status_code, 404)
