from django.test import override_settings

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class PricingTestCase(BaseTestCase):

    def test_anonymous(self):
        r = self.client.get("/pricing/")
        self.assertContains(r, "Unlimited Checks", status_code=200)

        # A subscription object should have NOT been created
        assert Subscription.objects.count() == 0

    def test_authenticated(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/pricing/")
        self.assertContains(r, "Unlimited Checks", status_code=200)

        # A subscription object still should have NOT been created
        assert Subscription.objects.count() == 0

    @override_settings(USE_PAYMENTS=True)
    def test_pricing_is_visible_for_all(self):
        for email in ("alice@example.org", "bob@example.org"):
            self.client.login(username=email, password="password")

            r = self.client.get("/about/")
            self.assertContains(r, "Pricing")

    def test_it_offers_to_switch(self):
        self.client.login(username="bob@example.org", password="password")

        r = self.client.get("/pricing/")
        self.assertContains(r, "To manage this team")
