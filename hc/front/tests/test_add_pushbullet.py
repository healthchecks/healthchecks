from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(PUSHBULLET_CLIENT_ID="t1", PUSHBULLET_CLIENT_SECRET="s1")
class AddPushbulletTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_pushbullet/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "www.pushbullet.com/authorize", status_code=200)
        self.assertContains(r, "Connect Pushbullet")

        # There should now be a key in session
        self.assertTrue("add_pushbullet" in self.client.session)

    @override_settings(PUSHBULLET_CLIENT_ID=None)
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
