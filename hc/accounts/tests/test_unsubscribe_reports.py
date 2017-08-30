from django.core import signing
from hc.test import BaseTestCase


class UnsubscribeReportsTestCase(BaseTestCase):

    def test_it_works(self):
        token = signing.Signer().sign("foo")
        url = "/accounts/unsubscribe_reports/alice/?token=%s" % token
        r = self.client.get(url)
        self.assertContains(r, "You have been unsubscribed")

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.reports_allowed)
