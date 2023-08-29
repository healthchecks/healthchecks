from __future__ import annotations

import time
from datetime import timedelta as td
from unittest.mock import patch

from django.core import signing
from django.utils.timezone import now

from hc.test import BaseTestCase


class UnsubscribeReportsTestCase(BaseTestCase):
    def test_it_unsubscribes(self) -> None:
        self.profile.next_report_date = now()
        self.profile.nag_period = td(hours=1)
        self.profile.next_nag_date = now()
        self.profile.save()

        sig = signing.TimestampSigner(salt="reports").sign("alice")
        url = "/accounts/unsubscribe_reports/%s/" % sig

        r = self.client.post(url)
        self.assertContains(r, "Unsubscribed")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.reports, "off")
        self.assertIsNone(self.profile.next_report_date)

        self.assertEqual(self.profile.nag_period.total_seconds(), 0)
        self.assertIsNone(self.profile.next_nag_date)

    def test_bad_signature_gets_rejected(self) -> None:
        url = "/accounts/unsubscribe_reports/invalid/"
        r = self.client.get(url)
        self.assertContains(r, "Incorrect Link")

    def test_it_serves_confirmation_form(self) -> None:
        sig = signing.TimestampSigner(salt="reports").sign("alice")
        url = "/accounts/unsubscribe_reports/%s/" % sig

        r = self.client.get(url)
        self.assertContains(r, "Please press the button below")
        self.assertNotContains(r, "submit()")

    def test_aged_signature_autosubmits(self) -> None:
        with patch("django.core.signing.time") as mock_time:
            mock_time.time.return_value = time.time() - 301
            signer = signing.TimestampSigner(salt="reports")
            sig = signer.sign("alice")

        url = "/accounts/unsubscribe_reports/%s/" % sig

        r = self.client.get(url)
        self.assertContains(r, "Please press the button below")
        self.assertContains(r, "submit()")

    def test_it_handles_missing_user(self) -> None:
        self.alice.delete()

        sig = signing.TimestampSigner(salt="reports").sign("alice")
        url = "/accounts/unsubscribe_reports/%s/" % sig

        r = self.client.post(url)
        self.assertContains(r, "Unsubscribed")
