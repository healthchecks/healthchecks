from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.template.loader import render_to_string

if settings.USE_PAYMENTS:
    import braintree
else:
    # hc.payments tests mock this object, so tests should
    # still be able to run:
    braintree = None


ADDRESS_KEYS = ("first_name", "last_name", "company", "street_address",
                "extended_address", "locality", "region", "postal_code",
                "country_code_alpha2")


class SubscriptionManager(models.Manager):

    def for_user(self, user):
        sub, created = Subscription.objects.get_or_create(user_id=user.id)
        return sub

    def by_transaction(self, transaction_id):
        try:
            tx = braintree.Transaction.find(transaction_id)
        except braintree.exceptions.NotFoundError:
            return None, None

        try:
            sub = self.get(customer_id=tx.customer_details.id)
        except Subscription.DoesNotExist:
            return None, None

        return sub, tx


class Subscription(models.Model):
    user = models.OneToOneField(User, models.CASCADE, blank=True, null=True)
    customer_id = models.CharField(max_length=36, blank=True)
    payment_method_token = models.CharField(max_length=35, blank=True)
    subscription_id = models.CharField(max_length=10, blank=True)
    plan_id = models.CharField(max_length=10, blank=True)
    address_id = models.CharField(max_length=2, blank=True)
    send_invoices = models.BooleanField(default=True)

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
        elif self.plan_id == "T144":
            return 144

        return 0

    def period(self):
        if self.plan_id.startswith("P"):
            return "month"
        elif self.plan_id.startswith("Y"):
            return "year"
        elif self.plan_id.startswith("T"):
            return "3 years"

        raise NotImplementedError("Unexpected plan: %s" % self.plan_id)

    @property
    def payment_method(self):
        if not self.payment_method_token:
            return None

        if not hasattr(self, "_pm"):
            self._pm = braintree.PaymentMethod.find(self.payment_method_token)
        return self._pm

    def _get_braintree_subscription(self):
        if not hasattr(self, "_sub"):
            self._sub = braintree.Subscription.find(self.subscription_id)
        return self._sub

    def get_client_token(self):
        return braintree.ClientToken.generate({
            "customer_id": self.customer_id
        })

    def update_payment_method(self, nonce):
        # Create customer record if it does not exist:
        if not self.customer_id:
            result = braintree.Customer.create({
                "email": self.user.email
            })
            if not result.is_success:
                return result

            self.customer_id = result.customer.id
            self.save()

        # Create payment method
        result = braintree.PaymentMethod.create({
            "customer_id": self.customer_id,
            "payment_method_nonce": nonce,
            "options": {"make_default": True}
        })

        if not result.is_success:
            return result

        self.payment_method_token = result.payment_method.token
        self.save()

        # Update an existing subscription to use this payment method
        if self.subscription_id:
            result = braintree.Subscription.update(self.subscription_id, {
                "payment_method_token": self.payment_method_token
            })

        if not result.is_success:
            return result

    def update_address(self, post_data):
        # Create customer record if it does not exist:
        if not self.customer_id:
            result = braintree.Customer.create({
                "email": self.user.email
            })
            if not result.is_success:
                return result

            self.customer_id = result.customer.id
            self.save()

        payload = {key: str(post_data.get(key)) for key in ADDRESS_KEYS}
        if self.address_id:
            result = braintree.Address.update(self.customer_id,
                                              self.address_id,
                                              payload)
        else:
            payload["customer_id"] = self.customer_id
            result = braintree.Address.create(payload)
            if result.is_success:
                self.address_id = result.address.id
                self.save()

        if not result.is_success:
            return result

    def setup(self, plan_id):
        result = braintree.Subscription.create({
            "payment_method_token": self.payment_method_token,
            "plan_id": plan_id
        })

        if result.is_success:
            self.subscription_id = result.subscription.id
            self.plan_id = plan_id
            self.save()

        return result

    def cancel(self):
        if self.subscription_id:
            braintree.Subscription.cancel(self.subscription_id)

        self.subscription_id = ""
        self.plan_id = ""
        self.save()

    def pm_is_card(self):
        pm = self.payment_method
        return isinstance(pm, braintree.credit_card.CreditCard)

    def pm_is_paypal(self):
        pm = self.payment_method
        return isinstance(pm, braintree.paypal_account.PayPalAccount)

    def next_billing_date(self):
        o = self._get_braintree_subscription()
        return o.next_billing_date

    @property
    def address(self):
        if not hasattr(self, "_address"):
            try:
                self._address = braintree.Address.find(self.customer_id,
                                                       self.address_id)
            except braintree.exceptions.NotFoundError:
                self._address = None

        return self._address

    def flattened_address(self):
        if self.address_id:
            ctx = {"a": self.address}
            return render_to_string("payments/address_plain.html", ctx)
        else:
            return self.user.email

    @property
    def transactions(self):
        if not hasattr(self, "_tx"):
            if not self.customer_id:
                self._tx = []
            else:
                self._tx = list(braintree.Transaction.search(braintree.TransactionSearch.customer_id == self.customer_id))

        return self._tx
