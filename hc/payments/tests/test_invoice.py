from mock import Mock, patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class InvoiceTestCase(BaseTestCase):

    def setUp(self):
        super(InvoiceTestCase, self).setUp()
        self.sub = Subscription(user=self.alice)
        self.sub.subscription_id = "test-id"
        self.sub.customer_id = "test-customer-id"
        self.sub.save()

    @patch("hc.payments.views.braintree")
    def test_it_works(self, mock_braintree):

        tx = Mock()
        tx.id = "abc123"
        tx.customer_details.id = "test-customer-id"
        tx.created_at = None
        mock_braintree.Transaction.find.return_value = tx

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/invoice/abc123/")
        self.assertContains(r, "ABC123")  # tx.id in uppercase
        self.assertContains(r, "alice@example.org")  # bill to

    @patch("hc.payments.views.braintree")
    def test_it_checks_customer_id(self, mock_braintree):

        tx = Mock()
        tx.id = "abc123"
        tx.customer_details.id = "test-another-customer-id"
        tx.created_at = None
        mock_braintree.Transaction.find.return_value = tx

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/invoice/abc123/")
        self.assertEqual(r.status_code, 403)

    @patch("hc.payments.views.braintree")
    def test_it_shows_company_data(self, mock_braintree):
        self.profile.bill_to = "Alice and Partners"
        self.profile.save()

        tx = Mock()
        tx.id = "abc123"
        tx.customer_details.id = "test-customer-id"
        tx.created_at = None
        mock_braintree.Transaction.find.return_value = tx

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/invoice/abc123/")
        self.assertContains(r, "Alice and Partners")
