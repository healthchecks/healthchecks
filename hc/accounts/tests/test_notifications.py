from datetime import timedelta as td

from django.utils.timezone import now
from hc.test import BaseTestCase


class NotificationsTestCase(BaseTestCase):
    def test_it_saves_reports_allowed_true(self):
        self.profile.reports_allowed = False
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"reports_allowed": "on", "nag_period": "0"}
        r = self.client.post("/accounts/profile/notifications/", form)
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.reports_allowed)
        self.assertIsNotNone(self.profile.next_report_date)

    def test_it_saves_reports_allowed_false(self):
        self.profile.reports_allowed = True
        self.profile.next_report_date = now()
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"nag_period": "0"}
        r = self.client.post("/accounts/profile/notifications/", form)
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.reports_allowed)
        self.assertIsNone(self.profile.next_report_date)

    def test_it_saves_hourly_nag_period(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"nag_period": "3600"}
        r = self.client.post("/accounts/profile/notifications/", form)
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nag_period.total_seconds(), 3600)
        self.assertIsNotNone(self.profile.next_nag_date)

    def test_it_does_not_save_nonstandard_nag_period(self):
        self.profile.nag_period = td(seconds=3600)
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"nag_period": "1234"}
        r = self.client.post("/accounts/profile/notifications/", form)
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nag_period.total_seconds(), 3600)
