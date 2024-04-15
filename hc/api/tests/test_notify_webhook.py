# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.lib.curl import CurlError
from hc.test import BaseTestCase


class NotifyWebhookTestCase(BaseTestCase):
    def _setup_data(
        self, value: str, status: str = "down", email_verified: bool = True
    ) -> None:
        self.check = Check(project=self.project)
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now()
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.created = now() - td(minutes=10)
        self.ping.n = 112233
        self.ping.body_raw = b"Body Line 1\nBody Line 2"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "webhook"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = status

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhook(self, mock_get: Mock) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        mock_get.return_value.status_code = 200

        self.channel.notify(self.flip)
        args, kwargs = mock_get.call_args
        self.assertEqual(args, ("get", "http://example"))

    @patch(
        "hc.api.transports.curl.request",
        autospec=True,
        side_effect=CurlError("Foo failed"),
    )
    def test_webhooks_handle_curl_errors(self, mock_get: Mock) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.flip)

        # The transport should have retried 3 times
        self.assertEqual(mock_get.call_count, 3)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Foo failed")

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "Foo failed")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_500(self, mock_get: Mock) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        mock_get.return_value.status_code = 500

        self.channel.notify(self.flip)

        # The transport should have retried 3 times
        self.assertEqual(mock_get.call_count, 3)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 500")

    @patch(
        "hc.api.transports.curl.request",
        autospec=True,
        side_effect=CurlError("Foo failed"),
    )
    def test_webhooks_dont_retry_when_sending_test_notifications(
        self, mock_get: Mock
    ) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.flip, is_test=True)

        # is_test flag is set, the transport should not retry:
        self.assertEqual(mock_get.call_count, 1)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Foo failed")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_support_variables(self, mock_get: Mock) -> None:
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

        self.channel.notify(self.flip)

        url = "http://host/%s/down/foo/bar/?name=Hello%%20World" % self.check.code

        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "get")
        self.assertEqual(args[1], url)
        self.assertEqual(kwargs["headers"], {})
        self.assertEqual(kwargs["timeout"], 10)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_variable_variables(self, mock_get: Mock) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://host/$$NAMETAG1",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.check.tags = "foo bar"
        self.check.save()

        self.channel.notify(self.flip)

        # $$NAMETAG1 should *not* get transformed to "foo"
        url = mock_get.call_args.args[1]
        self.assertEqual(url, "http://host/$TAG1")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_support_post(self, mock_request: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.com",
            "body_down": "The Time Is $NOW",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.check.save()

        self.channel.notify(self.flip)
        method, url = mock_request.call_args.args
        self.assertEqual(method, "post")
        self.assertEqual(url, "http://example.com")

        # spaces should not have been urlencoded:
        payload = mock_request.call_args.kwargs["data"].decode()
        self.assertTrue(payload.startswith("The Time Is 2"))

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_dollarsign_escaping(self, mock_get: Mock) -> None:
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

        self.channel.notify(self.flip)

        args, kwargs = mock_get.call_args
        self.assertEqual(args, ("get", "http://host/%24TAG1"))

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_up_events(self, mock_get: Mock) -> None:
        definition = {
            "method_up": "GET",
            "url_up": "http://bar",
            "body_up": "",
            "headers_up": {},
        }
        self._setup_data(json.dumps(definition), status="up")

        self.channel.notify(self.flip)

        args, kwargs = mock_get.call_args
        self.assertEqual(args, ("get", "http://bar"))

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_noop_up_events(self, mock_get: Mock) -> None:
        definition = {
            "method_up": "GET",
            "url_up": "",
            "body_up": "",
            "headers_up": {},
        }

        self._setup_data(json.dumps(definition), status="up")
        self.channel.notify(self.flip)

        mock_get.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_unicode_post_body(self, mock_request: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://foo.com",
            "body_down": "(╯°□°）╯︵ ┻━┻",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.check.save()

        self.channel.notify(self.flip)

        # unicode should be encoded into utf-8
        payload = mock_request.call_args.kwargs["data"]
        self.assertIsInstance(payload, bytes)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_post_headers(self, mock_request: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://foo.com",
            "body_down": "data",
            "headers_down": {"Content-Type": "application/json"},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.flip)

        args, kwargs = mock_request.call_args
        self.assertEqual(args, ("post", "http://foo.com"))
        self.assertEqual(kwargs["data"], b"data")
        self.assertEqual(kwargs["headers"], {"Content-Type": "application/json"})

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_get_headers(self, mock_request: Mock) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {"Content-Type": "application/json"},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.flip)

        args, kwargs = mock_request.call_args
        self.assertEqual(args, ("get", "http://foo.com"))
        self.assertEqual(kwargs["headers"], {"Content-Type": "application/json"})

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_allow_user_agent_override(self, mock_request: Mock) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {"User-Agent": "My-Agent"},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.flip)

        args, kwargs = mock_request.call_args
        self.assertEqual(args, ("get", "http://foo.com"))
        self.assertEqual(kwargs["headers"], {"User-Agent": "My-Agent"})

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_support_variables_in_headers(self, mock_request: Mock) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "body_down": "",
            "headers_down": {"X-Message": "$NAME is DOWN"},
        }

        self._setup_data(json.dumps(definition))
        self.check.name = "Foo"
        self.check.save()

        self.channel.notify(self.flip)

        args, kwargs = mock_request.call_args
        self.assertEqual(args, ("get", "http://foo.com"))
        self.assertEqual(kwargs["headers"], {"X-Message": "Foo is DOWN"})

    @override_settings(WEBHOOKS_ENABLED=False)
    def test_it_requires_webhooks_enabled(self) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://example",
            "body_down": "",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Webhook notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_non_ascii_in_headers(self, mock_request: Mock) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "headers_down": {"X-Foo": "bār"},
            "body_down": "",
        }

        self._setup_data(json.dumps(definition))
        self.check.save()

        self.channel.notify(self.flip)

        headers = mock_request.call_args.kwargs["headers"]
        self.assertEqual(headers["X-Foo"], "b&#257;r")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_latin1_in_headers(self, mock_request: Mock) -> None:
        definition = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "headers_down": {"X-Foo": "½"},
            "body_down": "",
        }

        self._setup_data(json.dumps(definition))
        self.check.save()

        self.channel.notify(self.flip)

        headers = mock_request.call_args.kwargs["headers"]
        self.assertEqual(headers["X-Foo"], "½")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_support_json_variable(self, mock_post: Mock) -> None:
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

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        body = json.loads(payload)
        self.assertEqual(body["name"], "Hello World")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_support_body_variable_in_body(self, mock_post: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "$BODY",
            "headers_down": {},
        }
        self._setup_data(json.dumps(definition))
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload, b"Body Line 1\nBody Line 2")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_dont_support_body_variable_in_url_and_headers(
        self, mock_post: Mock
    ) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org/$BODY",
            "body_down": "",
            "headers_down": {"User-Agent": "$BODY"},
        }

        self._setup_data(json.dumps(definition))

        ping_body = b"Body Line 1"
        self.ping = Ping(owner=self.check)
        self.flip.created = now()
        self.ping.body_raw = ping_body
        self.ping.save()

        self.channel.notify(self.flip)

        url = mock_post.call_args.args[1]
        self.assertTrue(url.endswith("$BODY"))
        headers = mock_post.call_args.kwargs["headers"]
        self.assertEqual(headers["User-Agent"], "$BODY")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_support_exitstatus_variable(self, mock_post: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "Exit status $EXITSTATUS",
            "headers_down": {},
        }
        self._setup_data(json.dumps(definition))
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload, b"Exit status 123")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_exitstatus_variable_with_last_ping_missing(
        self, mock_post: Mock
    ) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "Exit status $EXITSTATUS",
            "headers_down": {},
        }
        self._setup_data(json.dumps(definition))
        self.ping.delete()

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload, b"Exit status -1")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_handle_null_exitstatus(self, mock_post: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "Exit status $EXITSTATUS",
            "headers_down": {},
        }
        self._setup_data(json.dumps(definition))
        self.ping.exitstatus = None
        self.ping.save()

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload, b"Exit status -1")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_do_not_escape_name_variable(self, mock_post: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "$NAME",
            "headers_down": {},
        }
        self._setup_data(json.dumps(definition))

        self.check.name = 'Project "Foo"'
        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload, self.check.name.encode())

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_support_name_json_variable(self, mock_post: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "$NAME_JSON",
            "headers_down": {},
        }
        self._setup_data(json.dumps(definition))

        self.check.name = 'Project "Foo"'
        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload, json.dumps(self.check.name).encode())

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_do_not_escape_body_variable(self, mock_post: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "$BODY",
            "headers_down": {},
        }

        self._setup_data(json.dumps(definition))

        self.ping = Ping(owner=self.check)
        self.flip.created = now()
        self.ping.body_raw = b'Project "Foo"'
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload, b'Project "Foo"')

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_webhooks_support_body_json_variable(self, mock_post: Mock) -> None:
        definition = {
            "method_down": "POST",
            "url_down": "http://example.org",
            "body_down": "$BODY_JSON",
            "headers_down": {},
        }
        self._setup_data(json.dumps(definition))
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        expected_payload = json.dumps("Body Line 1\nBody Line 2").encode()
        self.assertEqual(payload, expected_payload)
