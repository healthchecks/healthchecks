from django.contrib.auth.models import User
from django.test import TestCase
from mock import patch
from requests.exceptions import ReadTimeout

from hc.api.models import Channel, Check, Notification


class NotifyTestCase(TestCase):

    @patch("hc.api.models.requests.get")
    def test_webhook(self, mock_get):
        alice = User(username="alice")
        alice.save()

        check = Check()
        check.status = "down"
        check.save()

        channel = Channel(user=alice, kind="webhook", value="http://example")
        channel.save()
        channel.checks.add(check)

        channel.notify(check)
        mock_get.assert_called_with(u"http://example", timeout=5)

    @patch("hc.api.models.requests.get", side_effect=ReadTimeout)
    def test_it_handles_requests_exceptions(self, mock_get):
        alice = User(username="alice")
        alice.save()

        check = Check()
        check.status = "down"
        check.save()

        channel = Channel(user=alice, kind="webhook", value="http://example")
        channel.save()
        channel.checks.add(check)

        channel.notify(check)

        assert Notification.objects.count() == 1
