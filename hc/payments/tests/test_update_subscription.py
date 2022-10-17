from __future__ import annotations

from unittest.mock import patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class UpdateSubscriptionTestCase(BaseTestCase):
    def _setup_mock(self, mock):
        """Set up Braintree calls that the controller will use."""

        mock.Subscription.create.return_value.is_success = True
        mock.Subscription.create.return_value.subscription.id = "t-sub-id"

    def run_update(self, plan_id="P20", nonce="fake-nonce"):
        form = {"plan_id": plan_id, "nonce": nonce}
        self.client.login(username="alice@example.org", password="password")
        return self.client.post("/pricing/update/", form, follow=True)

    @patch("hc.payments.models.braintree")
    def test_it_works(self, mock):
        self._setup_mock(mock)

        self.profile.sms_limit = 0
        self.profile.sms_sent = 1
        self.profile.call_limit = 0
        self.profile.calls_sent = 1
        self.profile.save()

        r = self.run_update()
        self.assertRedirects(r, "/accounts/profile/billing/")
        self.assertContains(r, "Your billing plan has been updated!")

        # Subscription should be filled out:
        sub = Subscription.objects.get(user=self.alice)
        self.assertEqual(sub.subscription_id, "t-sub-id")
        self.assertEqual(sub.plan_id, "P20")
        self.assertEqual(sub.plan_name, "Business ($20 / month)")

        # User's profile should have a higher limits
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ping_log_limit, 1000)
        self.assertEqual(self.profile.check_limit, 100)
        self.assertEqual(self.profile.team_limit, 9)
        self.assertEqual(self.profile.sms_limit, 50)
        self.assertEqual(self.profile.sms_sent, 0)
        self.assertEqual(self.profile.call_limit, 20)
        self.assertEqual(self.profile.calls_sent, 0)

        # braintree.Subscription.cancel should have not been called
        # because there was no previous subscription
        self.assertFalse(mock.Subscription.cancel.called)

        self.assertTrue(mock.Subscription.create.called)

    @patch("hc.payments.models.braintree")
    def test_supporter_works(self, mock):
        self._setup_mock(mock)

        self.profile.sms_limit = 0
        self.profile.sms_sent = 1
        self.profile.call_limit = 0
        self.profile.calls_sent = 1
        self.profile.save()

        r = self.run_update("S5")
        self.assertRedirects(r, "/accounts/profile/billing/")

        # Subscription should be filled out:
        sub = Subscription.objects.get(user=self.alice)
        self.assertEqual(sub.subscription_id, "t-sub-id")
        self.assertEqual(sub.plan_id, "S5")
        self.assertEqual(sub.plan_name, "Supporter ($5 / month)")

        # User's profile should have adjusted limits
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ping_log_limit, 1000)
        self.assertEqual(self.profile.check_limit, 20)
        self.assertEqual(self.profile.team_limit, 2)
        self.assertEqual(self.profile.sms_limit, 5)
        self.assertEqual(self.profile.sms_sent, 0)
        self.assertEqual(self.profile.call_limit, 5)
        self.assertEqual(self.profile.calls_sent, 0)

        # braintree.Subscription.cancel should have not been called
        assert not mock.Subscription.cancel.called

    @patch("hc.payments.models.braintree")
    def test_yearly_works(self, mock):
        self._setup_mock(mock)

        self.profile.sms_limit = 0
        self.profile.sms_sent = 1
        self.profile.call_limit = 0
        self.profile.calls_sent = 1
        self.profile.save()

        r = self.run_update("Y192")
        self.assertRedirects(r, "/accounts/profile/billing/")

        # Subscription should be filled out:
        sub = Subscription.objects.get(user=self.alice)
        self.assertEqual(sub.subscription_id, "t-sub-id")
        self.assertEqual(sub.plan_id, "Y192")
        self.assertEqual(sub.plan_name, "Business ($192 / year)")

        # User's profile should have a higher limits
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ping_log_limit, 1000)
        self.assertEqual(self.profile.check_limit, 100)
        self.assertEqual(self.profile.team_limit, 9)
        self.assertEqual(self.profile.sms_limit, 50)
        self.assertEqual(self.profile.sms_sent, 0)
        self.assertEqual(self.profile.call_limit, 20)
        self.assertEqual(self.profile.calls_sent, 0)

        # braintree.Subscription.cancel should have not been called
        assert not mock.Subscription.cancel.called

    @patch("hc.payments.models.braintree")
    def test_plus_works(self, mock):
        self._setup_mock(mock)

        self.profile.sms_limit = 0
        self.profile.sms_sent = 1
        self.profile.call_limit = 0
        self.profile.calls_sent = 1
        self.profile.save()

        r = self.run_update("P80")
        self.assertRedirects(r, "/accounts/profile/billing/")

        # Subscription should be filled out:
        sub = Subscription.objects.get(user=self.alice)
        self.assertEqual(sub.subscription_id, "t-sub-id")
        self.assertEqual(sub.plan_id, "P80")
        self.assertEqual(sub.plan_name, "Business Plus ($80 / month)")

        # User's profile should have a higher limits
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ping_log_limit, 1000)
        self.assertEqual(self.profile.check_limit, 1000)
        self.assertEqual(self.profile.team_limit, 500)
        self.assertEqual(self.profile.sms_limit, 500)
        self.assertEqual(self.profile.sms_sent, 0)
        self.assertEqual(self.profile.call_limit, 100)
        self.assertEqual(self.profile.calls_sent, 0)

        # braintree.Subscription.cancel should have not been called
        assert not mock.Subscription.cancel.called

    @patch("hc.payments.models.braintree")
    def test_it_cancels(self, mock):
        self._setup_mock(mock)

        self.sub = Subscription(user=self.alice)
        self.sub.subscription_id = "test-id"
        self.sub.plan_id = "P20"
        self.sub.plan_name = "Business ($20/mo)"
        self.sub.save()

        self.profile.sms_limit = 1
        self.profile.sms_sent = 1
        self.profile.call_limit = 1
        self.profile.calls_sent = 1
        self.profile.save()

        r = self.run_update("")
        self.assertRedirects(r, "/accounts/profile/billing/")
        self.assertContains(r, "Your billing plan has been updated!")

        # Subscription should be cleared
        sub = Subscription.objects.get(user=self.alice)
        self.assertEqual(sub.subscription_id, "")
        self.assertEqual(sub.plan_id, "")
        self.assertEqual(sub.plan_name, "")

        # User's profile should have standard limits
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ping_log_limit, 100)
        self.assertEqual(self.profile.check_limit, 20)
        self.assertEqual(self.profile.team_limit, 2)
        self.assertEqual(self.profile.sms_limit, 5)
        self.assertEqual(self.profile.call_limit, 0)

        self.assertTrue(mock.Subscription.cancel.called)

    def test_bad_plan_id(self):
        r = self.run_update(plan_id="this-is-wrong")
        self.assertEqual(r.status_code, 400)

    @patch("hc.payments.models.braintree")
    def test_it_cancels_previous_subscription(self, mock):
        self._setup_mock(mock)

        sub = Subscription(user=self.alice)
        sub.subscription_id = "prev-sub"
        sub.save()

        r = self.run_update()
        self.assertRedirects(r, "/accounts/profile/billing/")
        self.assertTrue(mock.Subscription.cancel.called)

    @patch("hc.payments.models.braintree")
    def test_subscription_creation_failure(self, mock):
        mock.Subscription.create.return_value.is_success = False
        mock.Subscription.create.return_value.message = "sub failure"

        r = self.run_update()
        self.assertRedirects(r, "/accounts/profile/billing/")
        self.assertContains(r, "sub failure")

    @patch("hc.payments.models.braintree")
    def test_failed_plan_change_resets_limits(self, mock):
        # Initial state: the user has a subscription and a high check limit:
        sub = Subscription.objects.for_user(self.alice)
        sub.subscription_id = "old-sub-id"
        sub.save()

        self.profile.check_limit = 1000
        self.profile.save()

        # Simulate a subscription creation failure:
        mock.Subscription.create.return_value.is_success = False
        mock.Subscription.create.return_value.message = "sub failure"

        r = self.run_update()

        # It should cancel the current plan
        self.assertTrue(mock.Subscription.cancel.called)

        # It should clear out the limits:
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.check_limit, 20)

        # And it should show the error message from API:
        self.assertRedirects(r, "/accounts/profile/billing/")
        self.assertContains(r, "sub failure")

    @patch("hc.payments.models.braintree")
    def test_it_updates_payment_method(self, mock):
        # Initial state: the user has a subscription and a high check limit:
        sub = Subscription.objects.for_user(self.alice)
        sub.plan_id = "P20"
        sub.subscription_id = "old-sub-id"
        sub.save()

        r = self.run_update()

        # It should update the existing subscription
        self.assertTrue(mock.Subscription.update.called)
        self.assertRedirects(r, "/accounts/profile/billing/")
        self.assertContains(r, "Your payment method has been updated!")
