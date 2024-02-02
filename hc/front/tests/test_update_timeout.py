from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Check
from hc.test import BaseTestCase


class UpdateTimeoutTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check(project=self.project, status="up")
        self.check.last_ping = now()
        self.check.save()

        self.url = f"/checks/{self.check.code}/timeout/"
        self.redirect_url = f"/projects/{self.project.code}/checks/"

    def test_it_works(self) -> None:
        payload = {"kind": "simple", "timeout": 3600, "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")
        self.assertEqual(self.check.timeout.total_seconds(), 3600)
        self.assertEqual(self.check.grace.total_seconds(), 60)

        # alert_after should be updated too
        assert self.check.last_ping
        expected_aa = self.check.last_ping + td(seconds=3600 + 60)
        self.assertEqual(self.check.alert_after, expected_aa)

    def test_redirect_preserves_querystring(self) -> None:
        referer = self.redirect_url + "?tag=foo"
        payload = {"kind": "simple", "timeout": 3600, "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload, HTTP_REFERER=referer)
        self.assertRedirects(r, referer)

    def test_it_does_not_update_status_to_up(self) -> None:
        self.check.last_ping = now() - td(days=2)
        self.check.status = "down"
        self.check.save()

        # 1 week:
        payload = {"kind": "simple", "timeout": 3600 * 24 * 7, "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, data=payload)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "down")

    def test_it_updates_status_to_down(self) -> None:
        self.check.last_ping = now() - td(hours=1)
        self.check.status = "up"
        self.check.alert_after = self.check.going_down_after()
        self.check.save()

        # 1 + 1 minute:
        payload = {"kind": "simple", "timeout": 60, "grace": 60}
        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, data=payload)

        self.check.refresh_from_db()
        # The status should have been changed to "down"
        self.assertEqual(self.check.status, "down")
        self.assertIsNone(self.check.alert_after)

        # It should also create a Flip object for downtime bookkeeping:
        flip = self.check.flip_set.get()
        self.assertEqual(flip.old_status, "up")
        self.assertEqual(flip.new_status, "down")
        self.assertTrue(flip.processed)

    def test_it_saves_cron_expression(self) -> None:
        payload = {"kind": "cron", "schedule": "5 * * * *", "tz": "UTC", "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "cron")
        self.assertEqual(self.check.schedule, "5 * * * *")

    def test_it_validates_cron_expression(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        samples = ["* invalid *", "1,2 61 * * *", "0 0 31 2 *"]

        for sample in samples:
            payload = {"kind": "cron", "schedule": sample, "tz": "UTC", "grace": 60}

            r = self.client.post(self.url, data=payload)
            self.assertEqual(r.status_code, 400)

        # Check should still have its original data:
        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")

    def test_it_rejects_six_field_cron_expression(self) -> None:
        payload = {
            "kind": "cron",
            "schedule": "* * * * * *",  # six fields instead of five
            "tz": "UTC",
            "grace": 60,
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 400)

        # Check should still have its original data:
        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")

    def test_it_validates_tz(self) -> None:
        payload = {
            "kind": "cron",
            "schedule": "* * * * *",
            "tz": "not-a-tz",
            "grace": 60,
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 400)

        # Check should still have its original data:
        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")

    def test_it_rejects_missing_schedule(self) -> None:
        # tz field is omitted so this should fail:
        payload = {"kind": "cron", "grace": 60, "tz": "UTC"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_missing_tz(self) -> None:
        # tz field is omitted so this should fail:
        payload = {"kind": "cron", "schedule": "* * * * *", "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 400)

    def test_it_saves_oncalendar_expression(self) -> None:
        payload = {"kind": "oncalendar", "schedule": "12:34", "tz": "UTC", "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "oncalendar")
        self.assertEqual(self.check.schedule, "12:34")

    def test_it_saves_multiline_oncalendar_expression(self) -> None:
        schedule = """
            01-01 12:00 America/New_York
            02-01 12:00 Europe/Paris
        """
        payload = {"kind": "oncalendar", "schedule": schedule, "tz": "UTC", "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "oncalendar")
        self.assertIn("Paris", self.check.schedule)

    def test_it_validates_oncalendar_expression(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        samples = ["*-*-* invalid", "12:99", "0-0"]

        for sample in samples:
            payload = {
                "kind": "oncalendar",
                "schedule": sample,
                "tz": "UTC",
                "grace": 60,
            }

            r = self.client.post(self.url, data=payload)
            self.assertEqual(r.status_code, 400)

        # Check should still have its original data:
        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")

    def test_team_access_works(self) -> None:
        payload = {"kind": "simple", "timeout": 7200, "grace": 60}

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, data=payload)

        check = Check.objects.get(code=self.check.code)
        assert check.timeout.total_seconds() == 7200

    def test_it_handles_bad_uuid(self) -> None:
        url = "/checks/not-uuid/timeout/"
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self) -> None:
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/timeout/"
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 404

    def test_it_checks_ownership(self) -> None:
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_allows_cross_team_access(self) -> None:
        payload = {"kind": "simple", "timeout": 3600, "grace": 60}

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        payload = {"kind": "simple", "timeout": 3600, "grace": 60}

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 403)
