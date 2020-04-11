import json
from unittest.mock import patch

from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(SLACK_CLIENT_ID="fake-client-id")
class AddSlackCompleteTestCase(BaseTestCase):
    @patch("hc.front.views.requests.post")
    def test_it_handles_oauth_response(self, mock_post):
        session = self.client.session
        session["add_slack"] = ("foo", str(self.project.code))
        session.save()

        oauth_response = {
            "ok": True,
            "team_name": "foo",
            "incoming_webhook": {"url": "http://example.org", "channel": "bar"},
        }

        mock_post.return_value.text = json.dumps(oauth_response)
        mock_post.return_value.json.return_value = oauth_response

        url = "/integrations/add_slack_btn/?code=12345678&state=foo"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "The Slack integration has been added!")

        ch = Channel.objects.get()
        self.assertEqual(ch.slack_team, "foo")
        self.assertEqual(ch.slack_channel, "bar")
        self.assertEqual(ch.slack_webhook_url, "http://example.org")
        self.assertEqual(ch.project, self.project)

        # Session should now be clean
        self.assertFalse("add_slack" in self.client.session)

    def test_it_avoids_csrf(self):
        session = self.client.session
        session["add_slack"] = ("foo", str(self.project.code))
        session.save()

        url = "/integrations/add_slack_btn/?code=12345678&state=bar"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

    @patch("hc.front.views.requests.post")
    def test_it_handles_oauth_error(self, mock_post):
        session = self.client.session
        session["add_slack"] = ("foo", str(self.project.code))
        session.save()

        oauth_response = {"ok": False, "error": "something went wrong"}

        mock_post.return_value.text = json.dumps(oauth_response)
        mock_post.return_value.json.return_value = oauth_response

        url = "/integrations/add_slack_btn/?code=12345678&state=foo"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "something went wrong")

    @override_settings(SLACK_CLIENT_ID=None)
    def test_it_requires_client_id(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/add_slack_btn/?code=12345678&state=foo")
        self.assertEqual(r.status_code, 404)
