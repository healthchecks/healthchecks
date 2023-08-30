from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(LINENOTIFY_CLIENT_ID="t1", LINENOTIFY_CLIENT_SECRET="s1")
class AddLineNotifyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_linenotify/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "notify-bot.line.me/oauth/authorize", status_code=200)
        self.assertContains(r, "Connect LINE Notify")

        # There should now be a key in session
        self.assertTrue("add_linenotify" in self.client.session)

    @override_settings(LINENOTIFY_CLIENT_ID=None)
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
