from django.core import mail
from mock import patch
from requests.exceptions import ConnectionError, Timeout

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyTestCase(BaseTestCase):

    def _setup_data(self, kind, value, status="down", email_verified=True):
        self.check = Check()
        self.check.status = status
        self.check.save()

        self.channel = Channel(user=self.alice)
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
            "get",  u"http://example",
            headers={"User-Agent": "healthchecks.io"}, timeout=5)

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

    def test_email(self):
        self._setup_data("email", "alice@example.org")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

    def test_it_skips_unverified_email(self):
        self._setup_data("email", "alice@example.org", email_verified=False)
        self.channel.notify(self.check)

        assert Notification.objects.count() == 1
        n = Notification.objects.first()
        self.assertEqual(n.error, "Email not verified")
        self.assertEqual(len(mail.outbox), 0)

    @patch("hc.api.transports.requests.request")
    def test_pd(self, mock_post):
        self._setup_data("pd", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        json = kwargs["json"]
        self.assertEqual(json["event_type"], "trigger")

    @patch("hc.api.transports.requests.request")
    def test_slack(self, mock_post):
        self._setup_data("slack", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        json = kwargs["json"]
        attachment = json["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Never")

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
    def test_hipchat(self, mock_post):
        self._setup_data("hipchat", "123")
        mock_post.return_value.status_code = 204

        self.channel.notify(self.check)
        n = Notification.objects.first()
        self.assertEqual(n.error, "")

        args, kwargs = mock_post.call_args
        json = kwargs["json"]
        self.assertIn("DOWN", json["message"])

    @patch("hc.api.transports.requests.request")
    def test_pushover(self, mock_post):
        self._setup_data("po", "123|0")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        json = kwargs["data"]
        self.assertIn("DOWN", json["title"])

    @patch("hc.api.transports.requests.request")
    def test_victorops(self, mock_post):
        self._setup_data("victorops", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        json = kwargs["json"]
        self.assertEqual(json["message_type"], "CRITICAL")
