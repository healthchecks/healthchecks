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
            print("getting subscription over network")
            self._sub = braintree.Subscription.find(self.subscription_id)

        return self._sub

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
