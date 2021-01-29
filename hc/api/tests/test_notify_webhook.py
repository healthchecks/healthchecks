# coding: utf-8

from datetime import timedelta as td
import json
from unittest.mock import patch

from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase
from requests.exceptions import ConnectionError, Timeout
from django.test.utils import override_settings


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

    @patch("hc.api.transports.requests.request")
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
            headers={"User-Agent": "healthchecks.io"},
            timeout=5,
        )

    @patch("hc.api.transports.requests.request", side_effect=Timeout)
    def test_webhooks_handle_timeouts(self, mock_get):
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
        self.assertEqual(n.error, "Connection timed out")

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "Connection timed out")

    @patch("hc.api.transports.requests.request", side_effect=ConnectionError)
    def test_webhooks_handle_connection_errors(self, mock_get):
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
        self.assertEqual(n.error, "Connection failed")

    @patch("hc.api.transports.requests.request")
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

    @patch("hc.api.transports.requests.request", side_effect=Timeout)
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
        self.assertEqual(n.error, "Connection timed out")

    @patch("hc.api.transports.requests.request")
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
        self.assertEqual(kwargs["headers"], {"User-Agent": "healthchecks.io"})
        self.assertEqual(kwargs["timeout"], 5)

    @patch("hc.api.transports.requests.request")
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
        args, kwargs = mock_get.call_args
        self.assertEqual(args[1], "http://host/$TAG1")

    @patch("hc.api.transports.requests.request")
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
        mock_get.assert_called_with(
            "get", url, headers={"User-Agent": "healthchecks.io"}, timeout=5
        )

    @patch("hc.api.transports.requests.request")
    def test_webhooks_handle_up_events(self, mock_get):
        definition = {
            "method_up": "GET",
            "url_up": "http://bar",
            "body_up": "",
            "headers_up": {},
        }
        self._setup_data(json.dumps(definition), status="up")

        self.channel.notify(self.check)

        mock_get.assert_called_with(
            "get", "http://bar", headers={"User-Agent": "healthchecks.io"}, timeout=5
        )

    @patch("hc.api.transports.requests.request")
    def test_webhooks_handle_noop_up_events(self, mock_get):
        definition = {
            "method_up": "GET",
            "url_up": "",
            "body_up": "",
            "headers_up": {},
        }

        self._setup_data(json.dumps(definition), status="up")
        self.channel.notify(self.check)

        self.assertFalse(mock_get.called)
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.requests.request")
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
        args, kwargs = mock_request.call_args

        # unicode should be encoded into utf-8
        self.assertIsInstance(kwargs["data"], bytes)

    @patch("hc.api.transports.requests.request")
    def test_webhooks_handle_post_headers(self, mock_request):
        definition = {
            "method_down": "POST",
            "url_down": "http://foo.com",
            "body_down": "data",
            "headers_down": {"Content-Type": "application/json"},
        }

        self._setup_data(json.dumps(definition))
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

        self._setup_data(json.dumps(definition))
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

        self._setup_data(json.dumps(definition))
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

        self._setup_data(json.dumps(definition))
        self.check.name = "Foo"
        self.check.save()

        self.channel.notify(self.check)

        headers = {"User-Agent": "healthchecks.io", "X-Message": "Foo is DOWN"}
        mock_request.assert_called_with(
            "get", "http://foo.com", headers=headers, timeout=5
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
