from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(SLACK_CLIENT_ID="fake-client-id")
class AddSlackBtnTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_slack_btn/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Setup Guide", status_code=200)

    def test_slack_button(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "slack.com/oauth/v2/authorize", status_code=200)

        # There should now be a key in session
        self.assertTrue("add_slack" in self.client.session)

    @override_settings(SLACK_CLIENT_ID=None)
    def test_it_requires_client_id(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(SLACK_ENABLED=False)
    def test_it_handles_disabled_integration(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
