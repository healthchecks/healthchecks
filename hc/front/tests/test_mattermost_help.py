from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(MATTERMOST_ENABLED=True, SITE_NAME="Mychecks")
class AddSlackHelpTestCase(BaseTestCase):
    def test_instructions_work(self) -> None:
        r = self.client.get("/integrations/mattermost/")
        self.assertContains(r, "please sign into Mychecks", status_code=200)
        self.assertContains(
            r, "click on <strong>Add Integration</strong>", status_code=200
        )

    @override_settings(MATTERMOST_ENABLED=False)
    def test_it_requires_mattermost_enabled(self) -> None:
        r = self.client.get("/integrations/mattermost/")
        self.assertEqual(r.status_code, 404)
