from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


class AddHipChatTestCase(BaseTestCase):
    url = "/integrations/add_hipchat/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "appropriate HipChat room")

    def test_it_returns_capabilities(self):
        r = self.client.get("/integrations/hipchat/capabilities/")
        self.assertContains(r, "installedUrl")

    @patch("hc.front.views.Channel.refresh_hipchat_access_token")
    @patch("hc.front.views.requests.get")
    def test_it_adds_channel(self, mock_get, mock_refresh):
        mock_get.return_value.json.return_value = {
            "oauthId": "test-id"
        }
        mock_get.return_value.text = "{}"

        self.client.login(username="alice@example.org", password="password")

        s = "https://api.hipchat.com/foo"
        r = self.client.post(self.url + "?installable_url=%s" % s)
        self.assertEqual(r.status_code, 302)

        self.assertTrue(mock_refresh.called)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "hipchat")
        self.assertEqual(c.value, "{}")
