from django.contrib.auth.models import User
from django.test import TestCase
from hc.payments.models import Subscription


class PricingTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

    def test_anonymous(self):
        r = self.client.get("/pricing/")
        self.assertContains(r, "Unlimited Checks", status_code=200)

        # A subscription object should have NOT been created
        assert Subscription.objects.count() == 0

    def test_authenticated(self):
        self.client.login(username="alice", password="password")

        r = self.client.get("/pricing/")
        self.assertContains(r, "Unlimited Checks", status_code=200)

        # A subscription object should have been created
        assert Subscription.objects.count() == 1
