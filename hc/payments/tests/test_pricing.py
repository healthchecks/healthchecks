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

        # A subscription object should have been created
        assert Subscription.objects.count() == 1
