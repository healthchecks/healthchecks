from django.contrib.auth.models import User
from django.test import TestCase
from hc.payments.models import Subscription
from mock import patch


class GetClientTokenTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

    @patch("hc.payments.views.braintree")
    def test_it_works(self, mock_braintree):
        mock_braintree.ClientToken.generate.return_value = "test-token"
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/pricing/get_client_token/")
        self.assertContains(r, "test-token", status_code=200)

        # A subscription object should have been created
        assert Subscription.objects.count() == 1
