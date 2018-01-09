from mock import patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class UpdatePaymentMethodTestCase(BaseTestCase):

    def _setup_mock(self, mock):
        """ Set up Braintree calls that the controller will use. """

        mock.PaymentMethod.create.return_value.is_success = True
        mock.PaymentMethod.create.return_value.payment_method.token = "fake"

    @patch("hc.payments.models.braintree")
    def test_it_retrieves_paypal(self, mock):
        self._setup_mock(mock)

        mock.paypal_account.PayPalAccount = dict
        mock.credit_card.CreditCard = list
        mock.PaymentMethod.find.return_value = {"email": "foo@example.org"}

        self.sub = Subscription(user=self.alice)
        self.sub.payment_method_token = "fake-token"
        self.sub.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/billing/payment_method/")
        self.assertContains(r, "foo@example.org")

    @patch("hc.payments.models.braintree")
    def test_it_retrieves_cc(self, mock):
        self._setup_mock(mock)

        mock.paypal_account.PayPalAccount = list
        mock.credit_card.CreditCard = dict
        mock.PaymentMethod.find.return_value = {"masked_number": "1***2"}

        self.sub = Subscription(user=self.alice)
        self.sub.payment_method_token = "fake-token"
        self.sub.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/billing/payment_method/")
        self.assertContains(r, "1***2")

    @patch("hc.payments.models.braintree")
    def test_it_creates_payment_method(self, mock):
        self._setup_mock(mock)

        self.sub = Subscription(user=self.alice)
        self.sub.customer_id = "test-customer"
        self.sub.save()

        self.client.login(username="alice@example.org", password="password")
        form = {"payment_method_nonce": "test-nonce"}
        r = self.client.post("/accounts/profile/billing/payment_method/", form)

        self.assertRedirects(r, "/accounts/profile/billing/")

    @patch("hc.payments.models.braintree")
    def test_it_creates_customer(self, mock):
        self._setup_mock(mock)

        mock.Customer.create.return_value.is_success = True
        mock.Customer.create.return_value.customer.id = "test-customer-id"

        self.sub = Subscription(user=self.alice)
        self.sub.save()

        self.client.login(username="alice@example.org", password="password")
        form = {"payment_method_nonce": "test-nonce"}
        self.client.post("/accounts/profile/billing/payment_method/", form)

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.customer_id, "test-customer-id")

    @patch("hc.payments.models.braintree")
    def test_it_updates_subscription(self, mock):
        self._setup_mock(mock)

        self.sub = Subscription(user=self.alice)
        self.sub.customer_id = "test-customer"
        self.sub.subscription_id = "fake-id"
        self.sub.save()

        mock.Customer.create.return_value.is_success = True
        mock.Customer.create.return_value.customer.id = "test-customer-id"

        self.client.login(username="alice@example.org", password="password")
        form = {"payment_method_nonce": "test-nonce"}
        self.client.post("/accounts/profile/billing/payment_method/", form)

        self.assertTrue(mock.Subscription.update.called)
