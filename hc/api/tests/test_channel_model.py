import json

from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


class ChannelModelTestCase(BaseTestCase):

    @patch("hc.api.models.requests.post")
    @patch("hc.api.models.requests.get")
    def test_it_refreshes_hipchat_access_token(self, mock_get, mock_post):
        mock_get.return_value.json.return_value = {
            "capabilities": {
                "oauth2Provider": {"tokenUrl": "http://example.org"}
            }
        }
        mock_post.return_value.json.return_value = {"expires_in": 100}

        channel = Channel(kind="hipchat", user=self.alice, value=json.dumps({
            "oauthId": "foo",
            "oauthSecret": "bar",
            "capabilitiesUrl": "http://example.org/capabilities.json"
        }))

        channel.refresh_hipchat_access_token()
        # It should fetch the remote capabilities document
        mock_get.assert_called()

        # It should request a token using a correct tokenUrl
        mock_post.assert_called()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://example.org")

        self.assertTrue("expires_at" in channel.value)
