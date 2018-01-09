from mock import patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class GetClientTokenTestCase(BaseTestCase):

    @patch("hc.payments.models.braintree")
    def test_it_works(self, mock_braintree):
        mock_braintree.ClientToken.generate.return_value = "test-token"
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/pricing/get_client_token/")
        self.assertContains(r, "test-token", status_code=200)

        # A subscription object should have been created
        assert Subscription.objects.count() == 1
