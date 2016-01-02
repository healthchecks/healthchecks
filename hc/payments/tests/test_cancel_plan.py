from django.contrib.auth.models import User
from django.test import TestCase
from hc.payments.models import Subscription
from mock import patch


class CancelPlanTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.sub = Subscription(user=self.alice)
        self.sub.subscription_id = "test-id"
        self.sub.plan_id = "P5"
        self.sub.save()

    @patch("hc.payments.views.braintree")
    def test_it_works(self, mock_braintree):

        self.client.login(username="alice", password="password")
        r = self.client.post("/pricing/cancel_plan/")
        self.assertRedirects(r, "/pricing/")

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.subscription_id, "")
        self.assertEqual(self.sub.plan_id, "")
