import json

from hc.api.models import Check, Channel, Notification
from hc.test import BaseTestCase


class ChannelsTestCase(BaseTestCase):

    def test_it_formats_complex_slack_value(self):
        ch = Channel(kind="slack", user=self.alice)
        ch.value = json.dumps({
            "ok": True,
            "team_name": "foo-team",
            "incoming_webhook": {
                "url": "http://example.org",
                "channel": "#bar"
            }
        })
        ch.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertContains(r, "foo-team", status_code=200)
        self.assertContains(r, "#bar")

    def test_it_shows_webhook_post_data(self):
        ch = Channel(kind="webhook", user=self.alice)
        ch.value = "http://down.example.com\nhttp://up.example.com\nfoobar"
        ch.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")

        self.assertEqual(r.status_code, 200)
        # These are inside a modal:
        self.assertContains(r, "<code>http://down.example.com</code>")
        self.assertContains(r, "<code>http://up.example.com</code>")
        self.assertContains(r, "<code>foobar</code>")

    def test_it_shows_pushover_details(self):
        ch = Channel(kind="po", user=self.alice)
        ch.value = "fake-key|0"
        ch.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "fake-key")
        self.assertContains(r, "(normal priority)")

    def test_it_shows_disabled_email(self):
        check = Check(user=self.alice, status="up")
        check.save()

        channel = Channel(user=self.alice, kind="email")
        channel.value = "alice@example.org"
        channel.save()

        n = Notification(owner=check, channel=channel, error="Invalid address")
        n.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "(bounced, disabled)")

    def test_it_shows_unconfirmed_email(self):
        channel = Channel(user=self.alice, kind="email")
        channel.value = "alice@example.org"
        channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "(unconfirmed)")
