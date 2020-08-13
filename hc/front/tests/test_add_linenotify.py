from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase

@override_settings(LINE_NOTIFY_ACCESS_TOKEN="foo")
class AddLineNotifyTestCase(BaseTestCase):
    url = "/integrations/add_linenotify/"

    def setUp(self):
        super(AddLineNotifyTestCase, self).setUp()
        self.url = "/projects/%s/add_linenotify/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "LineNotify")
