from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

if settings.USE_PAYMENTS:
    import braintree
else:
    # hc.payments tests mock this object, so tests should
    # still be able to run:
    braintree = None


ADDRESS_KEYS = (
    "company",
    "street_address",
    "extended_address",
    "locality",
    "region",
    "postal_code",
    "country_code_alpha2",
)


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

    def by_braintree_webhook(self, request):
        sig = str(request.POST["bt_signature"])
        payload = str(request.POST["bt_payload"])

        doc = braintree.WebhookNotification.parse(sig, payload)
        assert doc.kind == "subscription_charged_successfully"

        sub = self.get(subscription_id=doc.subscription.id)
        return sub, doc.subscription.transactions[0]


class Subscription(models.Model):
    user = models.OneToOneField(User, models.CASCADE, blank=True, null=True)
    customer_id = models.CharField(max_length=36, blank=True)
    payment_method_token = models.CharField(max_length=35, blank=True)
    subscription_id = models.CharField(max_length=10, blank=True)
    plan_id = models.CharField(max_length=10, blank=True)
    plan_name = models.CharField(max_length=50, blank=True)
    address_id = models.CharField(max_length=2, blank=True)
    send_invoices = models.BooleanField(default=True)
    invoice_email = models.EmailField(blank=True)

    objects = SubscriptionManager()

    @property
    def payment_method(self):
        if not self.subscription_id:
            return None

        if not hasattr(self, "_pm"):
            o = self._get_braintree_subscription()
            self._pm = braintree.PaymentMethod.find(o.payment_method_token)
        return self._pm

    @property
    def is_supporter(self):
        return self.plan_id in ("S5", "S48")

    @property
    def is_business(self):
        return self.plan_id in ("P20", "Y192")

    @property
    def is_business_plus(self):
        return self.plan_id in ("P80", "Y768")

    def is_annual(self):
        return self.plan_id in ("S48", "Y192", "Y768")

    def _get_braintree_subscription(self):
        if not hasattr(self, "_sub"):
            self._sub = braintree.Subscription.find(self.subscription_id)
        return self._sub

    def get_client_token(self):
        assert self.customer_id
        return braintree.ClientToken.generate({"customer_id": self.customer_id})

    def update_payment_method(self, nonce):
        assert self.subscription_id

        result = braintree.Subscription.update(
            self.subscription_id, {"payment_method_nonce": nonce}
        )

        if not result.is_success:
            return result

    def update_address(self, post_data):
        # Create customer record if it does not exist:
        if not self.customer_id:
            result = braintree.Customer.create({"email": self.user.email})
            if not result.is_success:
                return result

            self.customer_id = result.customer.id
            self.save()

        payload = {key: str(post_data.get(key)) for key in ADDRESS_KEYS}
        if self.address_id:
            result = braintree.Address.update(
                self.customer_id, self.address_id, payload
            )
        else:
            payload["customer_id"] = self.customer_id
            result = braintree.Address.create(payload)
            if result.is_success:
                self.address_id = result.address.id
                self.save()

        if not result.is_success:
            return result

    def setup(self, plan_id, nonce):
        result = braintree.Subscription.create(
            {"payment_method_nonce": nonce, "plan_id": plan_id}
        )

        if result.is_success:
            self.subscription_id = result.subscription.id
            self.plan_id = plan_id
            if plan_id == "P20":
                self.plan_name = "Business ($20 / month)"
            elif plan_id == "Y192":
                self.plan_name = "Business ($192 / year)"
            elif plan_id == "P80":
                self.plan_name = "Business Plus ($80 / month)"
            elif plan_id == "Y768":
                self.plan_name = "Business Plus ($768 / year)"
            elif plan_id == "S5":
                self.plan_name = "Supporter ($5 / month)"
            elif plan_id == "S48":
                self.plan_name = "Supporter ($48 / year)"

            self.save()

        if not result.is_success:
            return result

    def cancel(self):
        if self.subscription_id:
            braintree.Subscription.cancel(self.subscription_id)
            self.subscription_id = ""

        self.plan_id = ""
        self.plan_name = ""
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
                self._address = braintree.Address.find(
                    self.customer_id, self.address_id
                )
            except braintree.exceptions.NotFoundError:
                self._address = None

        return self._address

    @property
    def transactions(self):
        if not hasattr(self, "_tx"):
            if not self.customer_id:
                self._tx = []
            else:
                self._tx = list(
                    braintree.Transaction.search(
                        braintree.TransactionSearch.customer_id == self.customer_id
                    )
                )

        return self._tx
