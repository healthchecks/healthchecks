from django.contrib.auth.models import User
from django.test import TestCase
from hc.accounts.models import Profile
from hc.payments.models import Subscription
from mock import patch


class CreatePlanTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

    def _setup_mock(self, mock):
        """ Set up Braintree calls that the controller will use. """

        mock.Customer.create.return_value.is_success = True
        mock.Customer.create.return_value.customer.id = "test-customer-id"

        mock.PaymentMethod.create.return_value.is_success = True
        mock.PaymentMethod.create.return_value.payment_method.token = "t-token"

        mock.Subscription.create.return_value.is_success = True
        mock.Subscription.create.return_value.subscription.id = "t-sub-id"

    def run_create_plan(self, plan_id="P5"):
        form = {"plan_id": plan_id, "payment_method_nonce": "test-nonce"}
        self.client.login(username="alice", password="password")
        return self.client.post("/pricing/create_plan/", form)

    @patch("hc.payments.views.braintree")
    def test_it_works(self, mock):
        self._setup_mock(mock)

        r = self.run_create_plan()
        self.assertEqual(r.status_code, 302)

        # Subscription should be filled out:
        sub = Subscription.objects.get(user=self.alice)
        self.assertEqual(sub.customer_id, "test-customer-id")
        self.assertEqual(sub.payment_method_token, "t-token")
        self.assertEqual(sub.subscription_id, "t-sub-id")
        self.assertEqual(sub.plan_id, "P5")

        # User's profile should have a higher ping log limit:
        profile = Profile.objects.get(user=self.alice)
        self.assertEqual(profile.ping_log_limit, 1000)

        # braintree.Subscription.cancel should have not been called
        assert not mock.Subscription.cancel.called

    def test_bad_plan_id(self):
        r = self.run_create_plan(plan_id="this-is-wrong")
        self.assertEqual(r.status_code, 400)

    @patch("hc.payments.views.braintree")
    def test_it_cancels_previous_subscription(self, mock):
        self._setup_mock(mock)

        sub = Subscription(user=self.alice)
        sub.subscription_id = "prev-sub"
        sub.save()

        r = self.run_create_plan()
        self.assertEqual(r.status_code, 302)
        assert mock.Subscription.cancel.called
