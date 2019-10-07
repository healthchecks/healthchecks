from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase

TEST_CREDENTIALS = {
    "TWILIO_ACCOUNT": "foo",
    "TWILIO_AUTH": "foo",
    "TWILIO_FROM": "123",
    "TWILIO_USE_WHATSAPP": True,
}


@override_settings(**TEST_CREDENTIALS)
class AddWhatsAppTestCase(BaseTestCase):
    url = "/integrations/add_whatsapp/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Get a WhatsApp message")

    @override_settings(USE_PAYMENTS=True)
    def test_it_warns_about_limits(self):
        self.profile.sms_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "upgrade to a")

    def test_it_creates_channel(self):
        form = {
            "label": "My Phone",
            "value": "+1234567890",
            "down": "true",
            "up": "true",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "whatsapp")
        self.assertEqual(c.sms_number, "+1234567890")
        self.assertEqual(c.name, "My Phone")
        self.assertTrue(c.whatsapp_notify_down)
        self.assertTrue(c.whatsapp_notify_up)
        self.assertEqual(c.project, self.project)

    def test_it_obeys_up_down_flags(self):
        form = {"label": "My Phone", "value": "+1234567890"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "whatsapp")
        self.assertEqual(c.sms_number, "+1234567890")
        self.assertEqual(c.name, "My Phone")
        self.assertFalse(c.whatsapp_notify_down)
        self.assertFalse(c.whatsapp_notify_up)
        self.assertEqual(c.project, self.project)

    @override_settings(TWILIO_USE_WHATSAPP=False)
    def test_it_obeys_use_whatsapp_flag(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
