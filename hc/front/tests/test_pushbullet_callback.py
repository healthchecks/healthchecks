import json

from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


@override_settings(PUSHBULLET_CLIENT_ID="t1", PUSHBULLET_CLIENT_SECRET="s1")
class PushbulletCallbackTestCase(BaseTestCase):

    @patch("hc.front.views.requests.post")
    def test_it_works(self, mock_post):
        oauth_response = {"access_token": "test-token"}

        mock_post.return_value.text = json.dumps(oauth_response)
        mock_post.return_value.json.return_value = oauth_response

        url = "/integrations/add_pushbullet/?code=12345678"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, "/integrations/")
        self.assertContains(r, "The Pushbullet integration has been added!")

        ch = Channel.objects.get()
        self.assertEqual(ch.value, "test-token")
