from hc.api.models import Channel
from hc.test import BaseTestCase


class AddMsTeamsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = "/projects/%s/add_msteams/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Integration Settings", status_code=200)

    def test_it_works(self):
        form = {"value": "https://example.com/foo"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "msteams")
        self.assertEqual(c.value, "https://example.com/foo")
        self.assertEqual(c.project, self.project)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
