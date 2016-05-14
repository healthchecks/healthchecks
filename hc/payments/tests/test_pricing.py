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
    def test_pricing_is_hidden_for_team_members(self):

        self.client.login(username="bob@example.org", password="password")

        r = self.client.get("/about/")
        # Bob should not see pricing tab, as bob is currently on
        # Alice's team, but is not its owner.
        self.assertNotContains(r, "Pricing")

    @override_settings(USE_PAYMENTS=True)
    def test_pricing_is_visible_for_team_owners(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/about/")
        self.assertContains(r, "Pricing")
