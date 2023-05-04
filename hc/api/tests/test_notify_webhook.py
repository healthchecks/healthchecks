# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification, Ping
from hc.lib.curl import CurlError
from hc.test import BaseTestCase


class NotifyWebhookTestCase(BaseTestCase):
    def _setup_data(self, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "webhook"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_webhook(self, mock_get):
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        mock_get.return_value.status_code = 200

        self.channel.notify(self.check)
        mock_get.assert_called_with(
            "get",
            "http://example",
            headers={},
            timeout=10,
        )

    @patch("hc.api.transports.curl.request", side_effect=CurlError("Foo failed"))
    def test_webhooks_handle_curl_errors(self, mock_get):
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.check)

        # The transport should have retried 3 times
        self.assertEqual(mock_get.call_count, 3)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Foo failed")

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "Foo failed")

    @patch("hc.api.transports.curl.request")
    def test_webhooks_handle_500(self, mock_get):
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        mock_get.return_value.status_code = 500

        self.channel.notify(self.check)

        # The transport should have retried 3 times
        self.assertEqual(mock_get.call_count, 3)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 500")

    @patch("hc.api.transports.curl.request", side_effect=CurlError("Foo failed"))
    def test_webhooks_dont_retry_when_sending_test_notifications(self, mock_get):
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.check, is_test=True)

        # is_test flag is set, the transport should not retry:
        self.assertEqual(mock_get.call_count, 1)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Foo failed")

    @patch("hc.api.transports.curl.request")
    def test_webhooks_support_variables(self, mock_get):
        definition = {
            "method_down": "GET",
            "url_down": "http://host/$CODE/$STATUS/$TAG1/$TAG2/?name=$NAME",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.check.name = "Hello World"
        self.check.tags = "foo bar"
        self.check.save()

        self.channel.notify(self.check)

        url = "http://host/%s/down/foo/bar/?name=Hello%%20World" % self.check.code

        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "get")
        self.assertEqual(args[1], url)
        self.assertEqual(kwargs["headers"], {})
        self.assertEqual(kwargs["timeout"], 10)

    @patch("hc.api.transports.curl.request")
    def test_webhooks_handle_variable_variables(self, mock_get):
        definition = {
            "method_down": "GET",
            "url_down": "http://host/$$NAMETAG1",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.check.tags = "foo bar"
        self.check.save()

        self.channel.notify(self.check)

        # $$NAMETAG1 should *not* get transformed to "foo"
        url = mock_get.call_args.args[1]
        self.assertEqual(url, "http://host/$TAG1")

    @patch("hc.api.transports.curl.request")
    def test_webhooks_support_post(self, mock_request):
        definition = {
            "method_down": "POST",
            "url_down": "http://example.com",
            "body_down": "The Time Is $NOW",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.check.save()

        self.channel.notify(self.check)
        method, url = mock_request.call_args.args
        self.assertEqual(method, "post")
        self.assertEqual(url, "http://example.com")

        # spaces should not have been urlencoded:
        payload = mock_request.call_args.kwargs["data"].decode()
        self.assertTrue(payload.startswith("The Time Is 2"))

    @patch("hc.api.transports.curl.request")
    def test_webhooks_dollarsign_escaping(self, mock_get):
        # If name or tag contains what looks like a variable reference,
        # that should be left alone:
        definition = {
            "method_down": "GET",
            "url_down": "http://host/$NAME",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.check.name = "$TAG1"
        self.check.tags = "foo"
        self.check.save()

        self.channel.notify(self.check)

        url = "http://host/%24TAG1"
        mock_get.assert_called_with("get", url, headers={}, timeout=10)

    @patch("hc.api.transports.curl.request")
    def test_webhooks_handle_up_events(self, mock_get):
        definition = {
            "method_up": "GET",
            "url_up": "http://bar",
            "body_up": "",
            "headers_up": {},
        }
        self._setup_data(json.dumps(definition), status="up")

        self.channel.notify(self.check)

        mock_get.assert_called_with("get", "http://bar", headers={}, timeout=10)

    @patch("hc.api.transports.curl.request")
    def test_webhooks_handle_noop_up_events(self, mock_get):
        definition = {
            "method_up": "GET",
            "url_up": "",
            "body_up": "",
            "headers_up": {},
        }

        self._setup_data(json.dumps(definition), status="up")
        self.channel.notify(self.check)

        mock_get.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.curl.request")
    def test_webhooks_handle_unicode_post_body(self, mock_request):
        definition = {
            "method_down": "POST",
            "url_down": "http://foo.com",
            "body_down": "(╯°□°）╯︵ ┻━┻",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.check.save()

        self.channel.notify(self.check)

        # unicode should be encoded into utf-8
        payload = mock_request.call_args.kwargs["data"]
        self.assertIsInstance(payload, bytes)

    @patch("hc.api.transports.curl.request")
    def test_webhooks_handle_post_headers(self, mock_request):
        definition = {
            "method_down": "POST",
            "url_down": "http://foo.com",
            "body_down": "data",
            "headers_down": {"Content-Type": "application/json"},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.check)

        headers = {"Content-Type": "application/json"}
        mock_request.assert_called_with(
            "post", "http://foo.com", data=b"data", headers=headers, timeout=10
        )

    @patch("hc.api.transports.curl.request")
    def test_webhooks_handle_get_headers(self, mock_request):
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {"Content-Type": "application/json"},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.check)

        headers = {"Content-Type": "application/json"}
        mock_request.assert_called_with(
            "get", "http://foo.com", headers=headers, timeout=10
        )

    @patch("hc.api.transports.curl.request")
    def test_webhooks_allow_user_agent_override(self, mock_request):
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {"User-Agent": "My-Agent"},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.check)

        headers = {"User-Agent": "My-Agent"}
        mock_request.assert_called_with(
            "get", "http://foo.com", headers=headers, timeout=10
        )

    @patch("hc.api.transports.curl.request")
    def test_webhooks_support_variables_in_headers(self, mock_request):
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {"X-Message": "$NAME is DOWN"},
        }

        self._setup_data(json.dumps(definition))
        self.check.name = "Foo"
        self.check.save()

        self.channel.notify(self.check)

        headers = {"X-Message": "Foo is DOWN"}
        mock_request.assert_called_with(
            "get", "http://foo.com", headers=headers, timeout=10
        )

    @override_settings(WEBHOOKS_ENABLED=False)
    def test_it_requires_webhooks_enabled(self):
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Webhook notifications are not enabled.")

    @patch("hc.api.transports.curl.request")
    def test_webhooks_handle_non_ascii_in_headers(self, mock_request):
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "headers_down": {"X-Foo": "bār"},
            "body_down": "",
        }

        self._setup_data(json.dumps(definition))
        self.check.save()

        self.channel.notify(self.check)

        headers = mock_request.call_args.kwargs["headers"]
        self.assertEqual(headers["X-Foo"], "b&#257;r")

    @patch("hc.api.transports.curl.request")
    def test_webhooks_handle_latin1_in_headers(self, mock_request):
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "headers_down": {"X-Foo": "½"},
            "body_down": "",
        }

        self._setup_data(json.dumps(definition))
        self.check.save()

        self.channel.notify(self.check)

        headers = mock_request.call_args.kwargs["headers"]
        self.assertEqual(headers["X-Foo"], "½")

    @patch("hc.api.transports.curl.request")
    def test_webhooks_support_json_variable(self, mock_post):
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "$JSON",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.check.name = "Hello World"
        self.check.tags = "foo bar"
        self.check.save()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        body = json.loads(payload)
        self.assertEqual(body["name"], "Hello World")

    @patch("hc.api.transports.curl.request")
    def test_webhooks_support_body_variable_in_body(self, mock_post):
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "$BODY",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))

        ping_body = b"Body Line 1\nBody Line 2"
        self.ping = Ping(owner=self.check)
        self.ping.body_raw = ping_body
        self.ping.save()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload, ping_body)

    @patch("hc.api.transports.curl.request")
    def test_webhooks_dont_support_body_variable_in_url_and_headers(self, mock_post):
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org/$BODY",
            "body_down": "",
            "headers_down": {"User-Agent": "$BODY"},
        }

        self._setup_data(json.dumps(definition))

        ping_body = b"Body Line 1"
        self.ping = Ping(owner=self.check)
        self.ping.body_raw = ping_body
        self.ping.save()

        self.channel.notify(self.check)

        url = mock_post.call_args.args[1]
        self.assertTrue(url.endswith("$BODY"))
        headers = mock_post.call_args.kwargs["headers"]
        self.assertEqual(headers["User-Agent"], "$BODY")
