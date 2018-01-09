from mock import patch

from hc.payments.models import Subscription
from hc.test import BaseTestCase


class SetPlanTestCase(BaseTestCase):

    @patch("hc.payments.models.braintree")
    def test_it_saves_send_invoices_flag(self, mock):
        self.client.login(username="alice@example.org", password="password")

        form = {"save_send_invoices": True}
        self.client.post("/accounts/profile/billing/", form)
        sub = Subscription.objects.get()
        self.assertFalse(sub.send_invoices)
