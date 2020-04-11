from django.test.utils import override_settings
from hc.test import BaseTestCase


@override_settings(DISCORD_CLIENT_ID="t1", DISCORD_CLIENT_SECRET="s1")
class AddDiscordTestCase(BaseTestCase):
    def setUp(self):
        super(AddDiscordTestCase, self).setUp()
        self.url = "/projects/%s/add_discord/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Connect Discord", status_code=200)
        self.assertContains(r, "discordapp.com/api/oauth2/authorize")

        # There should now be a key in session
        self.assertTrue("add_discord" in self.client.session)

    @override_settings(DISCORD_CLIENT_ID=None)
    def test_it_requires_client_id(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
