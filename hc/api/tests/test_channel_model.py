import json

from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


class ChannelModelTestCase(BaseTestCase):

    @patch("hc.api.models.requests.post")
    def test_it_refreshes_hipchat_access_token(self, mock_post):
        mock_post.return_value.json.return_value = {"expires_in": 100}

        channel = Channel(kind="hipchat", user=self.alice, value=json.dumps({
            "oauthId": "foo",
            "oauthSecret": "bar"
        }))

        channel.refresh_hipchat_access_token()

        # It should request a token using a correct tokenUrl
        mock_post.assert_called()
        self.assertTrue("expires_at" in channel.value)
