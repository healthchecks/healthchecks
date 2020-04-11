from hc.api.models import Channel
from hc.test import BaseTestCase


class AddPagerTeamTestCase(BaseTestCase):
    def setUp(self):
        super(AddPagerTeamTestCase, self).setUp()
        self.url = "/projects/%s/add_pagerteam/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Pager Team")

    def test_it_works(self):
        form = {"value": "http://example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "pagerteam")
        self.assertEqual(c.value, "http://example.org")
        self.assertEqual(c.project, self.project)

    def test_it_rejects_bad_url(self):
        form = {"value": "not an URL"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Enter a valid URL")
