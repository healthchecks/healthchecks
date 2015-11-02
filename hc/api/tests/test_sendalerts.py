from datetime import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from hc.api.management.commands.sendalerts import handle_many
from hc.api.models import Check
from mock import patch


class SendAlertsTestCase(TestCase):

    @patch("hc.api.management.commands.sendalerts.handle_one")
    def test_it_handles_few(self, mock):
        alice = User(username="alice")
        alice.save()

        names = ["Check %d" % d for d in range(0, 10)]

        for name in names:
            check = Check(user=alice, name=name)
            check.alert_after = datetime(2000, 1, 1)
            check.status = "up"
            check.save()

        result = handle_many()
        assert result, "handle_many should return True"

        handled_names = []
        for args, kwargs in mock.call_args_list:
            handled_names.append(args[0].name)

        assert set(names) == set(handled_names)
