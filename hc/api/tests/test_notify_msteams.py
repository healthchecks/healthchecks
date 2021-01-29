# coding: utf-8

from datetime import timedelta as td
from unittest.mock import patch

from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase
from django.test.utils import override_settings


class NotifyTestCase(BaseTestCase):
    def _setup_data(self, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "msteams"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.requests.request")
    def test_msteams(self, mock_post):
        self._setup_data("http://example.com/webhook")
        mock_post.return_value.status_code = 200

        self.check.name = "_underscores_ & more"

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["@type"], "MessageCard")

        # summary and title should be the same, except
        # title should have any special HTML characters escaped
        self.assertEqual(payload["summary"], "“_underscores_ & more” is DOWN.")
        self.assertEqual(payload["title"], "“_underscores_ &amp; more” is DOWN.")

    @patch("hc.api.transports.requests.request")
    def test_msteams_escapes_html_and_markdown_in_desc(self, mock_post):
        self._setup_data("http://example.com/webhook")
        mock_post.return_value.status_code = 200

        self.check.desc = """
            TEST _underscore_ `backticks` <u>underline</u> \\backslash\\ "quoted"
        """

        self.channel.notify(self.check)

        args, kwargs = mock_post.call_args
        text = kwargs["json"]["sections"][0]["text"]

        self.assertIn(r"\_underscore\_", text)
        self.assertIn(r"\`backticks\`", text)
        self.assertIn("&lt;u&gt;underline&lt;/u&gt;", text)
        self.assertIn(r"\\backslash\\ ", text)
        self.assertIn("&quot;quoted&quot;", text)

    @override_settings(MSTEAMS_ENABLED=False)
    def test_it_requires_msteams_enabled(self):
        self._setup_data("http://example.com/webhook")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "MS Teams notifications are not enabled.")
