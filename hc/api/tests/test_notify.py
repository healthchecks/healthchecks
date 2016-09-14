import json

from django.core import mail
from django.test import override_settings
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase
from mock import patch
from requests.exceptions import ConnectionError, Timeout


class NotifyTestCase(BaseTestCase):

    def _setup_data(self, kind, value, status="down", email_verified=True):
        self.check = Check()
        self.check.status = status
        self.check.user = self.alice
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
            "get", u"http://example",
            headers={"User-Agent": "healthchecks.io"}, timeout=5)

    @patch("hc.api.transports.requests.request", side_effect=Timeout)
    def test_webhooks_handle_timeouts(self, mock_get):
        self._setup_data("webhook", "http://example")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Connection timed out")

    @patch("hc.api.transports.requests.request")
    def test_webhooks_ignore_up_events(self, mock_get):
        self._setup_data("webhook", "http://example", status="up")
        self.channel.notify(self.check)

        self.assertFalse(mock_get.called)
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.requests.request")
    def test_webhooks_support_variables(self, mock_get):
        template = "http://host/$CODE/$STATUS/$TAG1/$TAG2/?name=$NAME"
        self._setup_data("webhook", template)
        self.check.name = "Hello World"
        self.check.tags = "foo bar"
        self.check.save()

        self.channel.notify(self.check)

        url = u"http://host/%s/down/foo/bar/?name=Hello%%20World" \
            % self.check.code

        mock_get.assert_called_with(
            "get", url, headers={"User-Agent": "healthchecks.io"}, timeout=5)

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

        url = u"http://host/%24TAG1"
        mock_get.assert_called_with(
            "get", url, headers={"User-Agent": "healthchecks.io"}, timeout=5)

    @patch("hc.api.transports.requests.request")
    def test_webhook_fires_on_up_event(self, mock_get):
        self._setup_data("webhook", "http://foo\nhttp://bar", status="up")

        self.channel.notify(self.check)

        mock_get.assert_called_with(
            "get", "http://bar", headers={"User-Agent": "healthchecks.io"},
            timeout=5)

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

    @override_settings(USE_PAYMENTS=True)
    def test_email_contains_upgrade_notice(self):
        self._setup_data("email", "alice@example.org", status="up")
        self.profile.team_access_allowed = False
        self.profile.save()

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        # Check is up, payments are enabled, and the user does not have team
        # access: the email should contain upgrade note
        message = mail.outbox[0]
        html, _ = message.alternatives[0]
        assert "/pricing/" in html

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

    ### Test that the web hooks handle connection errors and error 500s
