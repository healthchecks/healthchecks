from django.core import mail
from mock import patch
from requests.exceptions import ReadTimeout

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyTestCase(BaseTestCase):

    def _setup_data(self, channel_kind, channel_value, email_verified=True):
        self.check = Check()
        self.check.status = "down"
        self.check.save()

        self.channel = Channel(user=self.alice)
        self.channel.kind = channel_kind
        self.channel.value = channel_value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.models.requests.get")
    def test_webhook(self, mock_get):
        self._setup_data("webhook", "http://example")
        mock_get.return_value.status_code = 200

        self.channel.notify(self.check)
        mock_get.assert_called_with(u"http://example", timeout=5)

    @patch("hc.api.models.requests.get", side_effect=ReadTimeout)
    def test_webhooks_handle_timeouts(self, mock_get):
        self._setup_data("webhook", "http://example")
        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

    def test_email(self):
        self._setup_data("email", "alice@example.org")
        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

    def test_it_skips_unverified_email(self):
        self._setup_data("email", "alice@example.org", email_verified=False)
        self.channel.notify(self.check)

        assert Notification.objects.count() == 0
        self.assertEqual(len(mail.outbox), 0)

    @patch("hc.api.models.requests.post")
    def test_pd(self, mock_post):
        self._setup_data("pd", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        assert "trigger" in kwargs["data"]
