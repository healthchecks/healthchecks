import json

from hc.api.models import Check, Channel, Notification
from hc.test import BaseTestCase


class ChannelsTestCase(BaseTestCase):
    def test_it_formats_complex_slack_value(self):
        ch = Channel(kind="slack", project=self.project)
        ch.value = json.dumps(
            {
                "ok": True,
                "team_name": "foo-team",
                "incoming_webhook": {"url": "http://example.org", "channel": "#bar"},
            }
        )
        ch.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertContains(r, "foo-team", status_code=200)
        self.assertContains(r, "#bar")

    def test_it_shows_webhook_post_data(self):
        ch = Channel(kind="webhook", project=self.project)
        ch.value = json.dumps(
            {
                "method_down": "POST",
                "url_down": "http://down.example.com",
                "body_down": "foobar",
                "headers_down": {},
                "method_up": "GET",
                "url_up": "http://up.example.com",
                "body_up": "",
                "headers_up": {},
            }
        )
        ch.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")

        self.assertEqual(r.status_code, 200)
        # These are inside a modal:
        self.assertContains(r, "http://down.example.com")
        self.assertContains(r, "http://up.example.com")
        self.assertContains(r, "foobar")

    def test_it_shows_pushover_details(self):
        ch = Channel(kind="po", project=self.project)
        ch.value = "fake-key|0"
        ch.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "(normal priority)")

    def test_it_shows_disabled_email(self):
        check = Check(project=self.project, status="up")
        check.save()

        channel = Channel(project=self.project, kind="email")
        channel.value = "alice@example.org"
        channel.save()

        n = Notification(owner=check, channel=channel, error="Invalid address")
        n.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Disabled")

    def test_it_shows_unconfirmed_email(self):
        channel = Channel(project=self.project, kind="email")
        channel.value = "alice@example.org"
        channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Unconfirmed")

    def test_it_shows_down_only_note_for_email(self):
        channel = Channel(project=self.project, kind="email")
        channel.value = json.dumps(
            {"value": "alice@example.org", "up": False, "down": True}
        )
        channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "(down only)")

    def test_it_shows_up_only_note_for_email(self):
        channel = Channel(project=self.project, kind="email")
        channel.value = json.dumps(
            {"value": "alice@example.org", "up": True, "down": False}
        )
        channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "(up only)")

    def test_it_shows_sms_number(self):
        ch = Channel(kind="sms", project=self.project)
        ch.value = json.dumps({"value": "+123"})
        ch.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "SMS to +123")

    def test_it_requires_current_project(self):
        self.profile.current_project = None
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertRedirects(r, "/")

    def test_it_shows_channel_issues_indicator(self):
        Channel.objects.create(kind="sms", project=self.project, last_error="x")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/")
        self.assertContains(r, "broken-channels", status_code=200)
