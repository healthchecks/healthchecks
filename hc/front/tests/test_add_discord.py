import json

from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


@override_settings(DISCORD_CLIENT_ID="t1", DISCORD_CLIENT_SECRET="s1")
class AddDiscordTestCase(BaseTestCase):
    url = "/integrations/add_discord/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Connect Discord", status_code=200)
        self.assertContains(r, "discordapp.com/api/oauth2/authorize")

        # There should now be a key in session
        self.assertTrue("discord" in self.client.session)

    @override_settings(DISCORD_CLIENT_ID=None)
    def test_it_requires_client_id(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    @patch("hc.front.views.requests.post")
    def test_it_handles_oauth_response(self, mock_post):
        session = self.client.session
        session["discord"] = "foo"
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
        self.assertRedirects(r, "/integrations/")
        self.assertContains(r, "The Discord integration has been added!")

        ch = Channel.objects.get()
        self.assertEqual(ch.discord_webhook_url, "foo")
        self.assertEqual(ch.project, self.project)

        # Session should now be clean
        self.assertFalse("discord" in self.client.session)

    def test_it_avoids_csrf(self):
        session = self.client.session
        session["discord"] = "foo"
        session.save()

        url = self.url + "?code=12345678&state=bar"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
