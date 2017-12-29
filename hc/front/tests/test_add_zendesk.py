import json

from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


@override_settings(ZENDESK_CLIENT_ID="t1", ZENDESK_CLIENT_SECRET="s1")
class AddZendeskTestCase(BaseTestCase):
    url = "/integrations/add_zendesk/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Connect Zendesk Support", status_code=200)

    def test_post_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"subdomain": "foo"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue("foo.zendesk.com" in r["Location"])

        # There should now be a key in session
        self.assertTrue("zendesk" in self.client.session)

    @override_settings(ZENDESK_CLIENT_ID=None)
    def test_it_requires_client_id(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    @patch("hc.front.views.requests.post")
    def test_it_handles_oauth_response(self, mock_post):
        session = self.client.session
        session["zendesk"] = "foo"
        session["subdomain"] = "foodomain"
        session.save()

        oauth_response = {"access_token": "test-token"}
        mock_post.return_value.text = json.dumps(oauth_response)
        mock_post.return_value.json.return_value = oauth_response

        url = self.url + "?code=12345678&state=foo"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, "/integrations/")
        self.assertContains(r, "The Zendesk integration has been added!")

        ch = Channel.objects.get()
        self.assertEqual(ch.zendesk_token, "test-token")
        self.assertEqual(ch.zendesk_subdomain, "foodomain")

        # Session should now be clean
        self.assertFalse("zendesk" in self.client.session)
        self.assertFalse("subdomain" in self.client.session)

    def test_it_avoids_csrf(self):
        session = self.client.session
        session["zendesk"] = "foo"
        session.save()

        url = self.url + "?code=12345678&state=bar"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
