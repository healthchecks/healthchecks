# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyOpsGenieTestCase(BaseTestCase):
    def _setup_data(self, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "opsgenie"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_opsgenie_with_legacy_value(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 202

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        self.assertEqual(mock_post.call_count, 1)
        url = mock_post.call_args.args[1]
        self.assertIn("api.opsgenie.com", url)
        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("DOWN", payload["message"])

    @patch("hc.api.transports.curl.request")
    def test_opsgenie_up(self, mock_post):
        self._setup_data("123", status="up")
        mock_post.return_value.status_code = 202

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        self.assertEqual(mock_post.call_count, 1)
        method, url = mock_post.call_args.args
        self.assertTrue(str(self.check.code) in url)

    @patch("hc.api.transports.curl.request")
    def test_opsgenie_with_json_value(self, mock_post):
        self._setup_data(json.dumps({"key": "456", "region": "eu"}))
        mock_post.return_value.status_code = 202

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        self.assertEqual(mock_post.call_count, 1)
        url = mock_post.call_args.args[1]
        self.assertIn("api.eu.opsgenie.com", url)

    @patch("hc.api.transports.curl.request")
    def test_opsgenie_returns_error(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 403
        mock_post.return_value.json.return_value = {"message": "Nice try"}

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, 'Received status code 403 with a message: "Nice try"')

    @patch("hc.api.transports.curl.request")
    def test_it_handles_non_json_error_response(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 403
        mock_post.return_value.json = Mock(side_effect=ValueError)

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 403")

    @override_settings(OPSGENIE_ENABLED=False)
    def test_it_requires_opsgenie_enabled(self):
        self._setup_data("123")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Opsgenie notifications are not enabled.")
