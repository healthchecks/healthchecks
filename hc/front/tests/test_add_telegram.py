from django.core import signing
from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


class AddTelegramTestCase(BaseTestCase):
    url = "/integrations/add_telegram/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "start@ExampleBot")

    def test_it_shows_confirmation(self):
        payload = signing.dumps((123, "group", "My Group"))

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?" + payload)
        self.assertContains(r, "My Group")

    def test_it_works(self):
        payload = signing.dumps((123, "group", "My Group"))

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url + "?" + payload, {})
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "telegram")
        self.assertEqual(c.telegram_id, 123)
        self.assertEqual(c.telegram_type, "group")
        self.assertEqual(c.telegram_name, "My Group")
        self.assertEqual(c.project, self.project)

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
