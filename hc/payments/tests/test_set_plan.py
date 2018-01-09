from mock import patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class SetPlanTestCase(BaseTestCase):

    def _setup_mock(self, mock):
        """ Set up Braintree calls that the controller will use. """

        mock.Subscription.create.return_value.is_success = True
        mock.Subscription.create.return_value.subscription.id = "t-sub-id"

    def run_set_plan(self, plan_id="P5"):
        form = {"plan_id": plan_id}
        self.client.login(username="alice@example.org", password="password")
        return self.client.post("/pricing/set_plan/", form, follow=True)

    @patch("hc.payments.models.braintree")
    def test_it_works(self, mock):
        self._setup_mock(mock)

        self.profile.sms_limit = 0
        self.profile.sms_sent = 1
        self.profile.save()

        r = self.run_set_plan()
        self.assertRedirects(r, "/accounts/profile/billing/")

        # Subscription should be filled out:
        sub = Subscription.objects.get(user=self.alice)
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

    @patch("hc.payments.models.braintree")
    def test_yearly_works(self, mock):
        self._setup_mock(mock)

        self.profile.sms_limit = 0
        self.profile.sms_sent = 1
        self.profile.save()

        r = self.run_set_plan("Y48")
        self.assertRedirects(r, "/accounts/profile/billing/")

        # Subscription should be filled out:
        sub = Subscription.objects.get(user=self.alice)
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

    @patch("hc.payments.models.braintree")
    def test_it_cancels(self, mock):
        self._setup_mock(mock)

        self.sub = Subscription(user=self.alice)
        self.sub.subscription_id = "test-id"
        self.sub.plan_id = "P5"
        self.sub.save()

        self.profile.sms_limit = 1
        self.profile.sms_sent = 1
        self.profile.save()

        r = self.run_set_plan("")
        self.assertRedirects(r, "/accounts/profile/billing/")

        # Subscription should be cleared
        sub = Subscription.objects.get(user=self.alice)
        self.assertEqual(sub.subscription_id, "")
        self.assertEqual(sub.plan_id, "")

        # User's profile should have standard limits
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ping_log_limit, 100)
        self.assertEqual(self.profile.check_limit, 20)
        self.assertEqual(self.profile.team_limit, 2)
        self.assertEqual(self.profile.sms_limit, 0)

        assert mock.Subscription.cancel.called

    def test_bad_plan_id(self):
        r = self.run_set_plan(plan_id="this-is-wrong")
        self.assertEqual(r.status_code, 400)

    @patch("hc.payments.models.braintree")
    def test_it_cancels_previous_subscription(self, mock):
        self._setup_mock(mock)

        sub = Subscription(user=self.alice)
        sub.subscription_id = "prev-sub"
        sub.save()

        r = self.run_set_plan()
        self.assertRedirects(r, "/accounts/profile/billing/")
        assert mock.Subscription.cancel.called

    @patch("hc.payments.models.braintree")
    def test_subscription_creation_failure(self, mock):
        self._setup_mock(mock)

        mock.Subscription.create.return_value.is_success = False
        mock.Subscription.create.return_value.message = "sub failure"

        r = self.run_set_plan()
        self.assertRedirects(r, "/accounts/profile/billing/")
        self.assertContains(r, "sub failure")
