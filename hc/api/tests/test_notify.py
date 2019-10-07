# coding: utf-8

from datetime import timedelta as td
import json

from django.core import mail
from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase
from mock import patch, Mock
from requests.exceptions import ConnectionError, Timeout
from django.test.utils import override_settings


class NotifyTestCase(BaseTestCase):
    def _setup_data(self, kind, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = kind
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.requests.request")
    def test_webhook(self, mock_get):
        self._setup_data("webhook", "http://example")
        mock_get.return_value.status_code = 200

        self.channel.notify(self.check)
        mock_get.assert_called_with(
            "get",
            "http://example",
            headers={"User-Agent": "healthchecks.io"},
            timeout=5,
        )

    @patch("hc.api.transports.requests.request", side_effect=Timeout)
    def test_webhooks_handle_timeouts(self, mock_get):
        self._setup_data("webhook", "http://example")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Connection timed out")

    @patch("hc.api.transports.requests.request", side_effect=ConnectionError)
    def test_webhooks_handle_connection_errors(self, mock_get):
        self._setup_data("webhook", "http://example")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Connection failed")

    @patch("hc.api.transports.requests.request")
    def test_webhooks_ignore_up_events(self, mock_get):
        self._setup_data("webhook", "http://example", status="up")
        self.channel.notify(self.check)

        self.assertFalse(mock_get.called)
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.requests.request")
    def test_webhooks_handle_500(self, mock_get):
        self._setup_data("webhook", "http://example")
        mock_get.return_value.status_code = 500

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 500")

    @patch("hc.api.transports.requests.request")
    def test_webhooks_support_tags(self, mock_get):
        template = "http://host/$TAGS"
        self._setup_data("webhook", template)
        self.check.tags = "foo bar"
        self.check.save()

        self.channel.notify(self.check)

        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "get")
        self.assertEqual(args[1], "http://host/foo%20bar")

    @patch("hc.api.transports.requests.request")
    def test_webhooks_support_variables(self, mock_get):
        template = "http://host/$CODE/$STATUS/$TAG1/$TAG2/?name=$NAME"
        self._setup_data("webhook", template)
        self.check.name = "Hello World"
        self.check.tags = "foo bar"
        self.check.save()

        self.channel.notify(self.check)

        url = "http://host/%s/down/foo/bar/?name=Hello%%20World" % self.check.code

        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "get")
        self.assertEqual(args[1], url)
        self.assertEqual(kwargs["headers"], {"User-Agent": "healthchecks.io"})
        self.assertEqual(kwargs["timeout"], 5)

    @patch("hc.api.transports.requests.request")
    def test_webhooks_support_post(self, mock_request):
        template = "http://example.com\n\nThe Time Is $NOW"
        self._setup_data("webhook", template)
        self.check.save()

        self.channel.notify(self.check)
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "post")
        self.assertEqual(args[1], "http://example.com")

        # spaces should not have been urlencoded:
        payload = kwargs["data"].decode()
        self.assertTrue(payload.startswith("The Time Is 2"))

    @patch("hc.api.transports.requests.request")
    def test_webhooks_dollarsign_escaping(self, mock_get):
        # If name or tag contains what looks like a variable reference,
        # that should be left alone:

        template = "http://host/$NAME"
        self._setup_data("webhook", template)
        self.check.name = "$TAG1"
        self.check.tags = "foo"
        self.check.save()

        self.channel.notify(self.check)

        url = "http://host/%24TAG1"
        mock_get.assert_called_with(
            "get", url, headers={"User-Agent": "healthchecks.io"}, timeout=5
        )

    @patch("hc.api.transports.requests.request")
    def test_webhook_fires_on_up_event(self, mock_get):
        self._setup_data("webhook", "http://foo\nhttp://bar", status="up")

        self.channel.notify(self.check)

        mock_get.assert_called_with(
            "get", "http://bar", headers={"User-Agent": "healthchecks.io"}, timeout=5
        )

    @patch("hc.api.transports.requests.request")
    def test_webhooks_handle_unicode_post_body(self, mock_request):
        template = "http://example.com\n\n(╯°□°）╯︵ ┻━┻"
        self._setup_data("webhook", template)
        self.check.save()

        self.channel.notify(self.check)
        args, kwargs = mock_request.call_args

        # unicode should be encoded into utf-8
        self.assertIsInstance(kwargs["data"], bytes)

    @patch("hc.api.transports.requests.request")
    def test_webhooks_handle_json_value(self, mock_request):
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {},
        }
        self._setup_data("webhook", json.dumps(definition))
        self.channel.notify(self.check)

        headers = {"User-Agent": "healthchecks.io"}
        mock_request.assert_called_with(
            "get", "http://foo.com", headers=headers, timeout=5
        )

    @patch("hc.api.transports.requests.request")
    def test_webhooks_handle_json_up_event(self, mock_request):
        definition = {
            "method_up": "GET",
            "url_up": "http://bar",
            "body_up": "",
            "headers_up": {},
        }

        self._setup_data("webhook", json.dumps(definition), status="up")
        self.channel.notify(self.check)

        headers = {"User-Agent": "healthchecks.io"}
        mock_request.assert_called_with("get", "http://bar", headers=headers, timeout=5)

    @patch("hc.api.transports.requests.request")
    def test_webhooks_handle_post_headers(self, mock_request):
        definition = {
            "method_down": "POST",
            "url_down": "http://foo.com",
            "body_down": "data",
            "headers_down": {"Content-Type": "application/json"},
        }

        self._setup_data("webhook", json.dumps(definition))
        self.channel.notify(self.check)

        headers = {"User-Agent": "healthchecks.io", "Content-Type": "application/json"}
        mock_request.assert_called_with(
            "post", "http://foo.com", data=b"data", headers=headers, timeout=5
        )

    @patch("hc.api.transports.requests.request")
    def test_webhooks_handle_get_headers(self, mock_request):
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {"Content-Type": "application/json"},
        }

        self._setup_data("webhook", json.dumps(definition))
        self.channel.notify(self.check)

        headers = {"User-Agent": "healthchecks.io", "Content-Type": "application/json"}
        mock_request.assert_called_with(
            "get", "http://foo.com", headers=headers, timeout=5
        )

    @patch("hc.api.transports.requests.request")
    def test_webhooks_allow_user_agent_override(self, mock_request):
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {"User-Agent": "My-Agent"},
        }

        self._setup_data("webhook", json.dumps(definition))
        self.channel.notify(self.check)

        headers = {"User-Agent": "My-Agent"}
        mock_request.assert_called_with(
            "get", "http://foo.com", headers=headers, timeout=5
        )

    @patch("hc.api.transports.requests.request")
    def test_webhooks_support_variables_in_headers(self, mock_request):
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {"X-Message": "$NAME is DOWN"},
        }

        self._setup_data("webhook", json.dumps(definition))
        self.check.name = "Foo"
        self.check.save()

        self.channel.notify(self.check)

        headers = {"User-Agent": "healthchecks.io", "X-Message": "Foo is DOWN"}
        mock_request.assert_called_with(
            "get", "http://foo.com", headers=headers, timeout=5
        )

    def test_email(self):
        self._setup_data("email", "alice@example.org")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertTrue("X-Bounce-Url" in email.extra_headers)
        self.assertTrue("List-Unsubscribe" in email.extra_headers)

    def test_email_transport_handles_json_value(self):
        payload = {"value": "alice@example.org", "up": True, "down": True}
        self._setup_data("email", json.dumps(payload))
        self.channel.notify(self.check)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")

    def test_it_skips_unverified_email(self):
        self._setup_data("email", "alice@example.org", email_verified=False)
        self.channel.notify(self.check)

        # If an email is not verified, it should be skipped over
        # without logging a notification:
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_checks_up_down_flags(self):
        payload = {"value": "alice@example.org", "up": True, "down": False}
        self._setup_data("email", json.dumps(payload))
        self.channel.notify(self.check)

        # This channel should not notify on "down" events:
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @patch("hc.api.transports.requests.request")
    def test_pd(self, mock_post):
        self._setup_data("pd", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "123")

    @patch("hc.api.transports.requests.request")
    def test_pd_complex(self, mock_post):
        self._setup_data("pd", json.dumps({"service_key": "456"}))
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "456")

    @patch("hc.api.transports.requests.request")
    def test_pagertree(self, mock_post):
        self._setup_data("pagertree", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")

    @patch("hc.api.transports.requests.request")
    def test_pagerteam(self, mock_post):
        self._setup_data("pagerteam", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")

    @patch("hc.api.transports.requests.request")
    def test_slack(self, mock_post):
        self._setup_data("slack", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        attachment = payload["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "an hour ago")

    @patch("hc.api.transports.requests.request")
    def test_slack_with_complex_value(self, mock_post):
        v = json.dumps({"incoming_webhook": {"url": "123"}})
        self._setup_data("slack", v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        self.assertEqual(args[1], "123")

    @patch("hc.api.transports.requests.request")
    def test_slack_handles_500(self, mock_post):
        self._setup_data("slack", "123")
        mock_post.return_value.status_code = 500

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 500")

    @patch("hc.api.transports.requests.request", side_effect=Timeout)
    def test_slack_handles_timeout(self, mock_post):
        self._setup_data("slack", "123")

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Connection timed out")

    @patch("hc.api.transports.requests.request")
    def test_slack_with_tabs_in_schedule(self, mock_post):
        self._setup_data("slack", "123")
        self.check.kind = "cron"
        self.check.schedule = "*\t* * * *"
        self.check.save()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertTrue(mock_post.called)

    @patch("hc.api.transports.requests.request")
    def test_hipchat(self, mock_post):
        self._setup_data("hipchat", "123")

        self.channel.notify(self.check)
        self.assertFalse(mock_post.called)
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.requests.request")
    def test_opsgenie(self, mock_post):
        self._setup_data("opsgenie", "123")
        mock_post.return_value.status_code = 202

        self.channel.notify(self.check)
        n = Notification.objects.first()
        self.assertEqual(n.error, "")

        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertIn("DOWN", payload["message"])

    @patch("hc.api.transports.requests.request")
    def test_opsgenie_up(self, mock_post):
        self._setup_data("opsgenie", "123", status="up")
        mock_post.return_value.status_code = 202

        self.channel.notify(self.check)
        n = Notification.objects.first()
        self.assertEqual(n.error, "")

        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args
        method, url = args
        self.assertTrue(str(self.check.code) in url)

    @patch("hc.api.transports.requests.request")
    def test_pushover(self, mock_post):
        self._setup_data("po", "123|0")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertIn("DOWN", payload["title"])

    @patch("hc.api.transports.requests.request")
    def test_pushover_up_priority(self, mock_post):
        self._setup_data("po", "123|0|2", status="up")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertIn("UP", payload["title"])
        self.assertEqual(payload["priority"], 2)
        self.assertIn("retry", payload)
        self.assertIn("expire", payload)

    @patch("hc.api.transports.requests.request")
    def test_victorops(self, mock_post):
        self._setup_data("victorops", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["message_type"], "CRITICAL")

    @patch("hc.api.transports.requests.request")
    def test_discord(self, mock_post):
        v = json.dumps({"webhook": {"url": "123"}})
        self._setup_data("discord", v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        attachment = payload["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "an hour ago")

    @patch("hc.api.transports.requests.request")
    def test_pushbullet(self, mock_post):
        self._setup_data("pushbullet", "fake-token")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["type"], "note")
        self.assertEqual(kwargs["headers"]["Access-Token"], "fake-token")

    @patch("hc.api.transports.requests.request")
    def test_telegram(self, mock_post):
        v = json.dumps({"id": 123})
        self._setup_data("telegram", v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["chat_id"], 123)
        self.assertTrue("The check" in payload["text"])

    @patch("hc.api.transports.requests.request")
    def test_sms(self, mock_post):
        self._setup_data("sms", "+1234567890")
        self.check.last_ping = now() - td(hours=2)

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertEqual(payload["To"], "+1234567890")
        self.assertFalse("\xa0" in payload["Body"])

        # sent SMS counter should go up
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sms_sent, 1)

    @patch("hc.api.transports.requests.request")
    def test_sms_handles_json_value(self, mock_post):
        value = {"label": "foo", "value": "+1234567890"}
        self._setup_data("sms", json.dumps(value))
        self.check.last_ping = now() - td(hours=2)

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertEqual(payload["To"], "+1234567890")

    @patch("hc.api.transports.requests.request")
    def test_sms_limit(self, mock_post):
        # At limit already:
        self.profile.last_sms_date = now()
        self.profile.sms_sent = 50
        self.profile.save()

        self._setup_data("sms", "+1234567890")

        self.channel.notify(self.check)
        self.assertFalse(mock_post.called)

        n = Notification.objects.get()
        self.assertTrue("Monthly SMS limit exceeded" in n.error)

    @patch("hc.api.transports.requests.request")
    def test_sms_limit_reset(self, mock_post):
        # At limit, but also into a new month
        self.profile.sms_sent = 50
        self.profile.last_sms_date = now() - td(days=100)
        self.profile.save()

        self._setup_data("sms", "+1234567890")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertTrue(mock_post.called)

    @patch("hc.api.transports.requests.request")
    def test_whatsapp(self, mock_post):
        definition = {"value": "+1234567890", "up": True, "down": True}

        self._setup_data("whatsapp", json.dumps(definition))
        self.check.last_ping = now() - td(hours=2)

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertEqual(payload["To"], "whatsapp:+1234567890")

        # sent SMS counter should go up
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sms_sent, 1)

    @patch("hc.api.transports.requests.request")
    def test_whatsapp_obeys_up_down_flags(self, mock_post):
        definition = {"value": "+1234567890", "up": True, "down": False}

        self._setup_data("whatsapp", json.dumps(definition))
        self.check.last_ping = now() - td(hours=2)

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 0)

        self.assertFalse(mock_post.called)

    @patch("hc.api.transports.requests.request")
    def test_whatsapp_limit(self, mock_post):
        # At limit already:
        self.profile.last_sms_date = now()
        self.profile.sms_sent = 50
        self.profile.save()

        definition = {"value": "+1234567890", "up": True, "down": True}
        self._setup_data("whatsapp", json.dumps(definition))

        self.channel.notify(self.check)
        self.assertFalse(mock_post.called)

        n = Notification.objects.get()
        self.assertTrue("Monthly message limit exceeded" in n.error)

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=True)
    def test_apprise_enabled(self, mock_apprise):
        self._setup_data("apprise", "123")

        mock_aobj = Mock()
        mock_aobj.add.return_value = True
        mock_aobj.notify.return_value = True
        mock_apprise.return_value = mock_aobj
        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

        self.check.status = "up"
        self.assertEqual(Notification.objects.count(), 1)

    @patch("apprise.Apprise")
    @override_settings(APPRISE_ENABLED=False)
    def test_apprise_disabled(self, mock_apprise):
        self._setup_data("apprise", "123")

        mock_aobj = Mock()
        mock_aobj.add.return_value = True
        mock_aobj.notify.return_value = True
        mock_apprise.return_value = mock_aobj
        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

    def test_not_implimented(self):
        self._setup_data("webhook", "http://example")
        self.channel.kind = "invalid"

        with self.assertRaises(NotImplementedError):
            self.channel.notify(self.check)
