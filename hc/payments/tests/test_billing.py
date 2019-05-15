from hc.payments.models import Subscription
from hc.test import BaseTestCase


class BillingCase(BaseTestCase):
    def test_it_disables_invoice_emailing(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"send_invoices": "0"}
        self.client.post("/accounts/profile/billing/", form)
        sub = Subscription.objects.get()
        self.assertFalse(sub.send_invoices)
        self.assertEqual(sub.invoice_email, "")

    def test_it_enables_invoice_emailing(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"send_invoices": "1"}
        self.client.post("/accounts/profile/billing/", form)
        sub = Subscription.objects.get()
        self.assertTrue(sub.send_invoices)
        self.assertEqual(sub.invoice_email, "")

    def test_it_saves_invoice_email(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"send_invoices": "2", "invoice_email": "invoices@example.org"}
        self.client.post("/accounts/profile/billing/", form)

        sub = Subscription.objects.get()
        self.assertTrue(sub.send_invoices)
        self.assertEqual(sub.invoice_email, "invoices@example.org")
