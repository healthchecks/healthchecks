from __future__ import annotations

from unittest.mock import Mock, patch

from django.utils.timezone import now

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class BillingHistoryTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.sub = Subscription(user=self.alice)
        self.sub.subscription_id = "test-id"
        self.sub.customer_id = "test-customer-id"
        self.sub.save()

    @patch("hc.payments.models.braintree")
    def test_it_works(self, mock_braintree):

        m1 = Mock(id="abc123", amount=123, created_at=now())
        m2 = Mock(id="def456", amount=456, created_at=now())
        mock_braintree.Transaction.search.return_value = [m1, m2]

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/billing/history/")
        self.assertContains(r, "123")
        self.assertContains(r, "456")
