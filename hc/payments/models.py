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
        if not hasattr(self, "_pm"):
            o = self._get_braintree_subscription()
            self._pm = braintree.PaymentMethod.find(o.payment_method_token)
        return self._pm

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

            self.save()

        return result

    def cancel(self, delete_customer=False):
        if self.subscription_id:
            braintree.Subscription.cancel(self.subscription_id)
            self.subscription_id = ""

        if self.customer_id and delete_customer:
            braintree.Customer.delete(self.customer_id)
            self.customer_id = ""

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

    def flattened_address(self):
        if self.address_id:
            ctx = {"a": self.address, "email": self.user.email}
            return render_to_string("payments/address_plain.html", ctx)
        else:
            return self.user.email

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
