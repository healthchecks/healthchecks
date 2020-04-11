from django.test.utils import override_settings
from hc.test import BaseTestCase


@override_settings(SLACK_CLIENT_ID="fake-client-id")
class AddSlackBtnTestCase(BaseTestCase):
    def setUp(self):
        super(AddSlackBtnTestCase, self).setUp()
        self.url = "/projects/%s/add_slack_btn/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Setup Guide", status_code=200)

    def test_slack_button(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "slack.com/oauth/v2/authorize", status_code=200)

        # There should now be a key in session
        self.assertTrue("add_slack" in self.client.session)

    @override_settings(SLACK_CLIENT_ID=None)
    def test_it_requires_client_id(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
