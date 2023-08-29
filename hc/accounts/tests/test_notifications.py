from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Check
from hc.test import BaseTestCase


class NotificationsTestCase(BaseTestCase):
    url = "/accounts/profile/notifications/"

    def _payload(self, **kwargs: str) -> dict[str, str]:
        result = {"reports": "monthly", "nag_period": "0", "tz": "Europe/Riga"}
        result.update(kwargs)
        return result

    def test_it_saves_reports_monthly(self) -> None:
        self.profile.reports = "off"
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.post(self.url, self._payload())
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.reports, "monthly")
        assert self.profile.next_report_date
        self.assertEqual(self.profile.next_report_date.day, 1)

    def test_it_saves_reports_weekly(self) -> None:
        self.profile.reports = "off"
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.post(self.url, self._payload(reports="weekly"))
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.reports, "weekly")
        assert self.profile.next_report_date
        self.assertEqual(self.profile.next_report_date.weekday(), 0)

    def test_it_saves_reports_off(self) -> None:
        self.profile.reports = "monthly"
        self.profile.next_report_date = now()
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.post(self.url, self._payload(reports="off"))
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.reports, "off")
        self.assertIsNone(self.profile.next_report_date)

    def test_it_sets_next_nag_date_when_setting_hourly_nag_period(self) -> None:
        Check.objects.create(project=self.project, status="down")

        self.client.login(username="alice@example.org", password="password")

        r = self.client.post(self.url, self._payload(nag_period="3600"))
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nag_period.total_seconds(), 3600)
        self.assertIsNotNone(self.profile.next_nag_date)

    def test_it_clears_next_nag_date_when_setting_hourly_nag_period(self) -> None:
        self.profile.next_nag_date = now() + td(minutes=30)
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.post(self.url, self._payload(nag_period="3600"))
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nag_period.total_seconds(), 3600)
        self.assertIsNone(self.profile.next_nag_date)

    def test_it_does_not_save_nonstandard_nag_period(self) -> None:
        self.profile.nag_period = td(seconds=3600)
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.post(self.url, self._payload(nag_period="1234"))
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nag_period.total_seconds(), 3600)

    def test_it_saves_tz(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.post(self.url, self._payload())
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.tz, "Europe/Riga")

    def test_it_ignores_bad_tz(self) -> None:
        self.profile.tz = "Europe/Riga"
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.post(self.url, self._payload(reports="weekly", tz="Foo/Bar"))
        self.assertEqual(r.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.reports, "weekly")
        self.assertEqual(self.profile.tz, "Europe/Riga")
