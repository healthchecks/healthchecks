from mock import patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class AddressTestCase(BaseTestCase):
    @patch("hc.payments.models.braintree")
    def test_it_retrieves_address(self, mock):
        mock.Address.find.return_value = {"company": "FooCo"}

        self.sub = Subscription(user=self.alice)
        self.sub.address_id = "aa"
        self.sub.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/billing/address/")
        self.assertContains(r, "FooCo")

    @patch("hc.payments.models.braintree")
    def test_it_creates_address(self, mock):
        mock.Address.create.return_value.is_success = True
        mock.Address.create.return_value.address.id = "bb"

        self.sub = Subscription(user=self.alice)
        self.sub.customer_id = "test-customer"
        self.sub.save()

        self.client.login(username="alice@example.org", password="password")
        form = {"company": "BarCo"}
        r = self.client.post("/accounts/profile/billing/address/", form)

        self.assertRedirects(r, "/accounts/profile/billing/")
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.address_id, "bb")

    @patch("hc.payments.models.braintree")
    def test_it_updates_address(self, mock):
        mock.Address.update.return_value.is_success = True

        self.sub = Subscription(user=self.alice)
        self.sub.customer_id = "test-customer"
        self.sub.address_id = "aa"
        self.sub.save()

        self.client.login(username="alice@example.org", password="password")
        form = {"company": "BarCo"}
        r = self.client.post("/accounts/profile/billing/address/", form)

        self.assertRedirects(r, "/accounts/profile/billing/")

    @patch("hc.payments.models.braintree")
    def test_it_creates_customer(self, mock):
        mock.Address.create.return_value.is_success = True
        mock.Address.create.return_value.address.id = "bb"

        mock.Customer.create.return_value.is_success = True
        mock.Customer.create.return_value.customer.id = "test-customer-id"

        self.sub = Subscription(user=self.alice)
        self.sub.save()

        self.client.login(username="alice@example.org", password="password")
        form = {"company": "BarCo"}
        self.client.post("/accounts/profile/billing/address/", form)

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.customer_id, "test-customer-id")
