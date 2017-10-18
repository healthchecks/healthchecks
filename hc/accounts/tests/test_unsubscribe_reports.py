from datetime import timedelta as td

from django.core import signing
from hc.test import BaseTestCase


class UnsubscribeReportsTestCase(BaseTestCase):

    def test_token_works(self):
        self.profile.nag_period = td(hours=1)
        self.profile.save()

        token = signing.Signer().sign("foo")
        url = "/accounts/unsubscribe_reports/alice/?token=%s" % token
        r = self.client.get(url)
        self.assertContains(r, "You have been unsubscribed")

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.reports_allowed)
        self.assertEqual(self.profile.nag_period.total_seconds(), 0)

    def test_bad_token_gets_rejected(self):
        url = "/accounts/unsubscribe_reports/alice/?token=invalid"
        r = self.client.get(url)
        self.assertContains(r, "Incorrect Link")

    def test_signed_username_works(self):
        sig = signing.TimestampSigner(salt="reports").sign("alice")
        url = "/accounts/unsubscribe_reports/%s/" % sig
        r = self.client.get(url)
        self.assertContains(r, "You have been unsubscribed")

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.reports_allowed)

    def test_bad_signature_gets_rejected(self):
        url = "/accounts/unsubscribe_reports/invalid/"
        r = self.client.get(url)
        self.assertContains(r, "Incorrect Link")
