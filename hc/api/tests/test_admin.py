from __future__ import annotations

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class ApiAdminTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project, tags="foo bar")

        self.alice.is_staff = True
        self.alice.is_superuser = True
        self.alice.save()

    def test_it_shows_channel_list_with_pushbullet(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        Channel.objects.create(
            project=self.project, kind="pushbullet", value="test-token"
        )

        r = self.client.get("/admin/api/channel/")
        self.assertContains(r, "ic-pushbullet")
