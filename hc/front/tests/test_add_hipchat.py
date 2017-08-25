import json

from django.core import signing
from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


class AddHipChatTestCase(BaseTestCase):
    url = "/integrations/add_hipchat/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "appropriate HipChat room")

    def test_instructions_work_when_logged_out(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Before adding HipChat integration, please")

    def test_it_redirects_to_addons_install(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 302)

    def test_it_returns_capabilities(self):
        r = self.client.get("/integrations/hipchat/capabilities/")
        self.assertContains(r, "callbackUrl")

    @patch("hc.api.models.Channel.refresh_hipchat_access_token")
    def test_callback_works(self, mock_refresh):
        state = signing.TimestampSigner().sign("alice")
        payload = json.dumps({"relayState": state, "foo": "foobar"})

        r = self.client.post("/integrations/hipchat/callback/", payload,
                             content_type="application/json")

        self.assertEqual(r.status_code, 200)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "hipchat")
        self.assertTrue("foobar" in c.value)

    @patch("hc.api.models.Channel.refresh_hipchat_access_token")
    def test_callback_rejects_bad_signature(self, mock_refresh):
        payload = json.dumps({"relayState": "alice:bad:sig", "foo": "foobar"})

        r = self.client.post("/integrations/hipchat/callback/", payload,
                             content_type="application/json")

        self.assertEqual(r.status_code, 400)
