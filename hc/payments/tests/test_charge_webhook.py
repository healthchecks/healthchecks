from mock import Mock, patch
from unittest import skipIf

from django.core import mail
from django.utils.timezone import now
from hc.payments.models import Subscription
from hc.test import BaseTestCase

try:
    import reportlab
except ImportError:
    reportlab = None


class ChargeWebhookTestCase(BaseTestCase):
    def setUp(self):
        super(ChargeWebhookTestCase, self).setUp()
        self.sub = Subscription(user=self.alice)
        self.sub.subscription_id = "test-id"
        self.sub.customer_id = "test-customer-id"
        self.sub.send_invoices = True
        self.sub.save()

        self.tx = Mock()
        self.tx.id = "abc123"
        self.tx.customer_details.id = "test-customer-id"
        self.tx.created_at = now()
        self.tx.currency_iso_code = "USD"
        self.tx.amount = 5
        self.tx.subscription_details.billing_period_start_date = now()
        self.tx.subscription_details.billing_period_end_date = now()

    @skipIf(reportlab is None, "reportlab not installed")
    @patch("hc.payments.views.Subscription.objects.by_braintree_webhook")
    def test_it_works(self, mock_getter):
        mock_getter.return_value = self.sub, self.tx

        r = self.client.post("/pricing/charge/")
        self.assertEqual(r.status_code, 200)

        # See if email was sent
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, "Invoice from Mychecks")
        self.assertEqual(msg.to, ["alice@example.org"])
        self.assertEqual(msg.attachments[0][0], "MS-HC-ABC123.pdf")

    @patch("hc.payments.views.Subscription.objects.by_braintree_webhook")
    def test_it_obeys_send_invoices_flag(self, mock_getter):
        mock_getter.return_value = self.sub, self.tx

        self.sub.send_invoices = False
        self.sub.save()

        r = self.client.post("/pricing/charge/")
        self.assertEqual(r.status_code, 200)

        # It should not send the email
        self.assertEqual(len(mail.outbox), 0)

    @skipIf(reportlab is None, "reportlab not installed")
    @patch("hc.payments.views.Subscription.objects.by_braintree_webhook")
    def test_it_uses_invoice_email(self, mock_getter):
        mock_getter.return_value = self.sub, self.tx

        self.sub.invoice_email = "alices_accountant@example.org"
        self.sub.save()

        r = self.client.post("/pricing/charge/")
        self.assertEqual(r.status_code, 200)

        # See if the email was sent to Alice's accountant:
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["alices_accountant@example.org"])
