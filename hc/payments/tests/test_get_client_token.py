from __future__ import annotations

from unittest.mock import patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class GetClientTokenTestCase(BaseTestCase):
    @patch("hc.payments.models.braintree")
    def test_it_works(self, mock_braintree):
        sub = Subscription(user=self.alice)
        sub.customer_id = "fake-customer-id"
        sub.save()

        mock_braintree.ClientToken.generate.return_value = "test-token"
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/pricing/token/")
        self.assertContains(r, "test-token", status_code=200)

        # A subscription object should have been created
        assert Subscription.objects.count() == 1
