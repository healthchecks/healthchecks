from django.test.utils import override_settings
from hc.test import BaseTestCase


@override_settings(SLACK_CLIENT_ID="fake-client-id")
class AddSlackHelpTestCase(BaseTestCase):
    def test_instructions_work(self):
        r = self.client.get("/integrations/add_slack/")
        self.assertContains(r, "Setup Guide", status_code=200)
