from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

if settings.USE_PAYMENTS:
    import braintree
else:
    # hc.payments tests mock this object, so tests should
    # still be able to run:
    braintree = None


class SubscriptionManager(models.Manager):

    def for_user(self, user):
        sub, created = Subscription.objects.get_or_create(user_id=user.id)
        return sub


class Subscription(models.Model):
    user = models.OneToOneField(User, models.CASCADE, blank=True, null=True)
    customer_id = models.CharField(max_length=36, blank=True)
    payment_method_token = models.CharField(max_length=35, blank=True)
    subscription_id = models.CharField(max_length=10, blank=True)
    plan_id = models.CharField(max_length=10, blank=True)

    objects = SubscriptionManager()

    def price(self):
        if self.plan_id == "P5":
            return 5
        elif self.plan_id == "P50":
            return 50
        elif self.plan_id == "Y48":
            return 48
        elif self.plan_id == "Y480":
            return 480

        return 0

    def period(self):
        if self.plan_id.startswith("P"):
            return "month"
        elif self.plan_id.startswith("Y"):
            return "year"

        raise NotImplementedError("Unexpected plan: %s" % self.plan_id)

    def _get_braintree_payment_method(self):
        if not hasattr(self, "_pm"):
            self._pm = braintree.PaymentMethod.find(self.payment_method_token)
        return self._pm

    def cancel(self):
        if self.subscription_id:
            braintree.Subscription.cancel(self.subscription_id)

        self.subscription_id = ""
        self.plan_id = ""
        self.save()

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
