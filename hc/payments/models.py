import braintree
from django.contrib.auth.models import User
from django.db import models


class Subscription(models.Model):
    user = models.OneToOneField(User, blank=True, null=True)
    customer_id = models.CharField(max_length=36, blank=True)
    payment_method_token = models.CharField(max_length=35, blank=True)
    subscription_id = models.CharField(max_length=10, blank=True)

    def _get_braintree_sub(self):
        if not hasattr(self, "_sub"):
            self._sub = braintree.Subscription.find(self.subscription_id)

        return self._sub

    def _get_braintree_payment_method(self):
        if not hasattr(self, "_pm"):
            self._pm = braintree.PaymentMethod.find(self.payment_method_token)

        return self._pm

    def is_active(self):
        if not self.subscription_id:
            return False

        o = self._get_braintree_sub()
        return o.status == "Active"

    def price(self):
        o = self._get_braintree_sub()
        return int(o.price)

    def next_billing_date(self):
        o = self._get_braintree_sub()
        return o.next_billing_date

    def pm_is_credit_card(self):
        return isinstance(self._get_braintree_payment_method(),
                          braintree.credit_card.CreditCard)

    def pm_is_paypal(self):
        return isinstance(self._get_braintree_payment_method(),
                          braintree.paypal_account.PayPalAccount)

    def card_type(self):
        o = self._get_braintree_payment_method()
        return o.card_type

    def last_4(self):
        o = self._get_braintree_payment_method()
        return o.last_4

    def paypal_email(self):
        o = self._get_braintree_payment_method()
        return o.email
