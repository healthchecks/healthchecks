from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(
    PUSHOVER_API_TOKEN="token", PUSHOVER_SUBSCRIPTION_URL="http://example.org"
)
class AddPushoverHelpTestCase(BaseTestCase):
    url = "/integrations/add_pushover/"

    @override_settings(PUSHOVER_API_TOKEN=None)
    def test_it_requires_api_token(self) -> None:
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_instructions_work_without_login(self) -> None:
        r = self.client.get(self.url)
        self.assertContains(r, "Setup Guide")
