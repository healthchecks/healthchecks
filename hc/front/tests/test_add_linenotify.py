from hc.api.models import Channel
from hc.test import BaseTestCase

class AddLineNotifyTestCase(BaseTestCase):
    url = "/integrations/add_linenotify/"

    def setUp(self):
        super(AddLineNotifyTestCase, self).setUp()
        self.url = "/projects/%s/add_linenotify/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "LineNotify")

    def test_it_works(self):
        form = {"token": "helloworld"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "linenotify")
        self.assertEqual(c.value, "helloworld")
        self.assertEqual(c.project, self.project)

    def test_it_handles_json_linenotify_value(self):
        c = Channel(kind="linenotify", value="foo123")
        self.assertEqual(c.linenotify_token, "foo123")

    def test_it_save_token(self):
        form = {"token": "foo123"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.value, "foo123")
