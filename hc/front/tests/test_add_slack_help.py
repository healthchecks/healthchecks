from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(SLACK_CLIENT_ID="fake-client-id")
class AddSlackHelpTestCase(BaseTestCase):
    def test_instructions_work(self) -> None:
        r = self.client.get("/integrations/add_slack/")
        self.assertContains(r, "Setup Guide", status_code=200)

    @override_settings(SLACK_CLIENT_ID=None)
    def test_it_requires_client_id(self) -> None:
        r = self.client.get("/integrations/add_slack/")
        self.assertEqual(r.status_code, 404)
