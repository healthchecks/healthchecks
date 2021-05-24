from datetime import timedelta as td

from django.utils.timezone import now
from hc.api.models import Check
from hc.test import BaseTestCase


class NotificationsTestCase(BaseTestCase):
    def test_it_saves_reports_monthly(self):
        self.profile.reports = "off"
        self.profile.reports_allowed = False
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"reports": "monthly", "nag_period": "0"}
        r = self.client.post("/accounts/profile/notifications/", form)
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.reports_allowed)
        self.assertEqual(self.profile.reports, "monthly")
        self.assertIsNotNone(self.profile.next_report_date)

    def test_it_saves_reports_off(self):
        self.profile.reports_allowed = True
        self.profile.reports = "monthly"
        self.profile.next_report_date = now()
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"reports": "off", "nag_period": "0"}
        r = self.client.post("/accounts/profile/notifications/", form)
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.reports_allowed)
        self.assertEqual(self.profile.reports, "off")
        self.assertIsNone(self.profile.next_report_date)

    def test_it_sets_next_nag_date_when_setting_hourly_nag_period(self):
        Check.objects.create(project=self.project, status="down")

        self.client.login(username="alice@example.org", password="password")

        form = {"reports": "off", "nag_period": "3600"}
        r = self.client.post("/accounts/profile/notifications/", form)
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nag_period.total_seconds(), 3600)
        self.assertIsNotNone(self.profile.next_nag_date)

    def test_it_clears_next_nag_date_when_setting_hourly_nag_period(self):
        self.profile.next_nag_date = now() + td(minutes=30)
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"reports": "off", "nag_period": "3600"}
        r = self.client.post("/accounts/profile/notifications/", form)
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nag_period.total_seconds(), 3600)
        self.assertIsNone(self.profile.next_nag_date)

    def test_it_does_not_save_nonstandard_nag_period(self):
        self.profile.nag_period = td(seconds=3600)
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"reports": "off", "nag_period": "1234"}
        r = self.client.post("/accounts/profile/notifications/", form)
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nag_period.total_seconds(), 3600)
