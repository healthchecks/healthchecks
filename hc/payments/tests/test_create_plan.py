from mock import patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class CreatePlanTestCase(BaseTestCase):

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
        self.client.login(username="alice@example.org", password="password")
        return self.client.post("/pricing/create_plan/", form, follow=True)

    @patch("hc.payments.views.braintree")
    def test_it_works(self, mock):
        self._setup_mock(mock)

        self.profile.sms_limit = 0
        self.profile.sms_sent = 1
        self.profile.save()

        r = self.run_create_plan()
        self.assertRedirects(r, "/pricing/")

        # Subscription should be filled out:
        sub = Subscription.objects.get(user=self.alice)
        self.assertEqual(sub.customer_id, "test-customer-id")
        self.assertEqual(sub.payment_method_token, "t-token")
        self.assertEqual(sub.subscription_id, "t-sub-id")
        self.assertEqual(sub.plan_id, "P5")

        # User's profile should have a higher limits
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ping_log_limit, 1000)
        self.assertEqual(self.profile.check_limit, 500)
        self.assertEqual(self.profile.team_limit, 9)
        self.assertEqual(self.profile.sms_limit, 50)
        self.assertEqual(self.profile.sms_sent, 0)

        # braintree.Subscription.cancel should have not been called
        assert not mock.Subscription.cancel.called

    @patch("hc.payments.views.braintree")
    def test_yearly_works(self, mock):
        self._setup_mock(mock)

        self.profile.sms_limit = 0
        self.profile.sms_sent = 1
        self.profile.save()

        r = self.run_create_plan("Y48")
        self.assertRedirects(r, "/pricing/")

        # Subscription should be filled out:
        sub = Subscription.objects.get(user=self.alice)
        self.assertEqual(sub.customer_id, "test-customer-id")
        self.assertEqual(sub.payment_method_token, "t-token")
        self.assertEqual(sub.subscription_id, "t-sub-id")
        self.assertEqual(sub.plan_id, "Y48")

        # User's profile should have a higher limits
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ping_log_limit, 1000)
        self.assertEqual(self.profile.check_limit, 500)
        self.assertEqual(self.profile.team_limit, 9)
        self.assertEqual(self.profile.sms_limit, 50)
        self.assertEqual(self.profile.sms_sent, 0)

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
        self.assertRedirects(r, "/pricing/")
        assert mock.Subscription.cancel.called

    @patch("hc.payments.views.braintree")
    def test_customer_creation_failure(self, mock):
        self._setup_mock(mock)

        mock.Customer.create.return_value.is_success = False
        mock.Customer.create.return_value.message = "Test Failure"

        r = self.run_create_plan()
        self.assertRedirects(r, "/pricing/")
        self.assertContains(r, "Test Failure")

    @patch("hc.payments.views.braintree")
    def test_pm_creation_failure(self, mock):
        self._setup_mock(mock)

        mock.PaymentMethod.create.return_value.is_success = False
        mock.PaymentMethod.create.return_value.message = "pm failure"

        r = self.run_create_plan()
        self.assertRedirects(r, "/pricing/")
        self.assertContains(r, "pm failure")

    @patch("hc.payments.views.braintree")
    def test_subscription_creation_failure(self, mock):
        self._setup_mock(mock)

        mock.Subscription.create.return_value.is_success = False
        mock.Subscription.create.return_value.message = "sub failure"

        r = self.run_create_plan()
        self.assertRedirects(r, "/pricing/")
        self.assertContains(r, "sub failure")
