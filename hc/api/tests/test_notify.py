from django.contrib.auth.models import User
from django.test import TestCase
from mock import patch

from hc.api.models import Channel, Check


class NotifyTestCase(TestCase):

    @patch("hc.api.models.requests")
    def test_webhook(self, mock_requests):
        alice = User(username="alice")
        alice.save()

        check = Check()
        check.status = "down"
        check.save()

        channel = Channel(user=alice, kind="webhook", value="http://example")
        channel.save()
        channel.checks.add(check)

        channel.notify(check)
        mock_requests.get.assert_called_with(u"http://example")
