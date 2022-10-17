from __future__ import annotations

from unittest.mock import patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class UpdatePaymentMethodTestCase(BaseTestCase):
    @patch("hc.payments.models.braintree")
    def test_it_retrieves_paypal(self, mock):
        mock.paypal_account.PayPalAccount = dict
        mock.credit_card.CreditCard = list
        mock.PaymentMethod.find.return_value = {"email": "foo@example.org"}

        Subscription.objects.create(user=self.alice, subscription_id="fake-id")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/billing/payment_method/")
        self.assertContains(r, "foo@example.org")

    @patch("hc.payments.models.braintree")
    def test_it_retrieves_cc(self, mock):
        mock.paypal_account.PayPalAccount = list
        mock.credit_card.CreditCard = dict
        mock.PaymentMethod.find.return_value = {"masked_number": "1***2"}

        Subscription.objects.create(user=self.alice, subscription_id="fake-id")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/billing/payment_method/")
        self.assertContains(r, "1***2")
