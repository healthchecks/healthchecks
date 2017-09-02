from mock import patch

from hc.accounts.models import Profile
from hc.payments.models import Subscription
from hc.test import BaseTestCase


class CancelPlanTestCase(BaseTestCase):

    def setUp(self):
        super(CancelPlanTestCase, self).setUp()
        self.sub = Subscription(user=self.alice)
        self.sub.subscription_id = "test-id"
        self.sub.plan_id = "P5"
        self.sub.save()

        self.profile.ping_log_limit = 1000
        self.profile.check_limit = 500
        self.profile.sms_limit = 50
        self.profile.save()

    @patch("hc.payments.models.braintree")
    def test_it_works(self, mock_braintree):

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/pricing/cancel_plan/")
        self.assertRedirects(r, "/pricing/")

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.subscription_id, "")
        self.assertEqual(self.sub.plan_id, "")

        # User's profile should have standard limits
        profile = Profile.objects.get(user=self.alice)
        self.assertEqual(profile.ping_log_limit, 100)
        self.assertEqual(profile.check_limit, 20)
        self.assertEqual(profile.team_limit, 2)
        self.assertEqual(profile.sms_limit, 0)
