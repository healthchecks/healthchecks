from django.core import signing
from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


@override_settings(TELEGRAM_TOKEN="fake-token")
class AddTelegramTestCase(BaseTestCase):
    url = "/integrations/add_telegram/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "start@ExampleBot")

    @override_settings(TELEGRAM_TOKEN=None)
    def test_it_requires_token(self):
        payload = signing.dumps((123, "group", "My Group"))

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?" + payload)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_confirmation(self):
        payload = signing.dumps((123, "group", "My Group"))

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?" + payload)
        self.assertContains(r, "My Group")

    def test_it_works(self):
        payload = signing.dumps((123, "group", "My Group"))

        self.client.login(username="alice@example.org", password="password")
        form = {"project": str(self.project.code)}
        r = self.client.post(self.url + "?" + payload, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "telegram")
        self.assertEqual(c.telegram_id, 123)
        self.assertEqual(c.telegram_type, "group")
        self.assertEqual(c.telegram_name, "My Group")
        self.assertEqual(c.project, self.project)

    def test_it_handles_bad_signature(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?bad-signature")
        self.assertContains(r, "Incorrect Link")

        self.assertFalse(Channel.objects.exists())

    @patch("hc.api.transports.requests.request")
    def test_it_sends_invite(self, mock_get):
        data = {
            "message": {
                "chat": {"id": 123, "title": "My Group", "type": "group"},
                "text": "/start",
            }
        }
        r = self.client.post(
            "/integrations/telegram/bot/", data, content_type="application/json"
        )

        self.assertEqual(r.status_code, 200)
        self.assertTrue(mock_get.called)

    @patch("hc.api.transports.requests.request")
    def test_bot_handles_bad_message(self, mock_get):
        samples = ["", "{}"]

        # text is missing
        samples.append({"message": {"chat": {"id": 123, "type": "group"}}})

        # bad chat type
        samples.append(
            {"message": {"chat": {"id": 123, "type": "invalid"}, "text": "/start"}}
        )

        for sample in samples:
            r = self.client.post(
                "/integrations/telegram/bot/", sample, content_type="application/json"
            )

            if sample == "":
                # Bad JSON payload
                self.assertEqual(r.status_code, 400)
            else:
                # JSON decodes but message structure not recognized
                self.assertEqual(r.status_code, 200)
