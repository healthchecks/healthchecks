import json

from hc.api.models import Channel
from hc.test import BaseTestCase


class EditWebhookTestCase(BaseTestCase):
    def setUp(self):
        super(EditWebhookTestCase, self).setUp()

        definition = {
            "method_down": "GET",
            "url_down": "http://example.org/down",
            "body_down": "$NAME is down",
            "headers_down": {"User-Agent": "My-Custom-UA"},
            "method_up": "GET",
            "url_up": "http://example.org/up",
            "body_up": "$NAME is up",
            "headers_up": {},
        }

        self.channel = Channel(project=self.project, kind="webhook")
        self.channel.name = "Call example.org"
        self.channel.value = json.dumps(definition)
        self.channel.save()

        self.url = "/integrations/%s/edit_webhook/" % self.channel.code

    def test_it_shows_form(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Webhook Settings")

        self.assertContains(r, "Call example.org")

        # down
        self.assertContains(r, "http://example.org/down")
        self.assertContains(r, "My-Custom-UA")
        self.assertContains(r, "$NAME is down")

        # up
        self.assertContains(r, "http://example.org/up")
        self.assertContains(r, "$NAME is up")

    def test_it_saves_form_and_redirects(self):
        form = {
            "name": "Call foo.com / bar.com",
            "method_down": "POST",
            "url_down": "http://foo.com",
            "headers_down": "X-Foo: 1\nX-Bar: 2",
            "body_down": "going down",
            "method_up": "POST",
            "url_up": "https://bar.com",
            "headers_up": "Content-Type: text/plain",
            "body_up": "going up",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.name, "Call foo.com / bar.com")

        down_spec = self.channel.down_webhook_spec
        self.assertEqual(down_spec["method"], "POST")
        self.assertEqual(down_spec["url"], "http://foo.com")
        self.assertEqual(down_spec["body"], "going down")
        self.assertEqual(down_spec["headers"], {"X-Foo": "1", "X-Bar": "2"})

        up_spec = self.channel.up_webhook_spec
        self.assertEqual(up_spec["method"], "POST")
        self.assertEqual(up_spec["url"], "https://bar.com")
        self.assertEqual(up_spec["body"], "going up")
        self.assertEqual(up_spec["headers"], {"Content-Type": "text/plain"})

    def test_it_requires_kind_webhook(self):
        self.channel.kind = "email"
        self.channel.value = "foo@example.org"
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 400)
