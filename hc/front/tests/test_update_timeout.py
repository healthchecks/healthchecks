from datetime import timedelta as td

from django.utils import timezone
from hc.api.models import Check
from hc.test import BaseTestCase


class UpdateTimeoutTestCase(BaseTestCase):
    def setUp(self):
        super(UpdateTimeoutTestCase, self).setUp()
        self.check = Check(project=self.project, status="up")
        self.check.last_ping = timezone.now()
        self.check.save()

        self.url = "/checks/%s/timeout/" % self.check.code
        self.redirect_url = "/projects/%s/checks/" % self.project.code

    def test_it_works(self):
        payload = {"kind": "simple", "timeout": 3600, "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")
        self.assertEqual(self.check.timeout.total_seconds(), 3600)
        self.assertEqual(self.check.grace.total_seconds(), 60)

        # alert_after should be updated too
        expected_aa = self.check.last_ping + td(seconds=3600 + 60)
        self.assertEqual(self.check.alert_after, expected_aa)

    def test_it_does_not_update_status(self):
        self.check.last_ping = timezone.now() - td(days=2)
        self.check.status = "down"
        self.check.save()

        # 1 week:
        payload = {"kind": "simple", "timeout": 3600 * 24 * 7, "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, data=payload)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "down")

    def test_it_saves_cron_expression(self):
        payload = {"kind": "cron", "schedule": "5 * * * *", "tz": "UTC", "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "cron")
        self.assertEqual(self.check.schedule, "5 * * * *")

    def test_it_validates_cron_expression(self):
        self.client.login(username="alice@example.org", password="password")
        samples = ["* invalid *", "1,2 3,* * * *"]

        for sample in samples:
            payload = {"kind": "cron", "schedule": sample, "tz": "UTC", "grace": 60}

            r = self.client.post(self.url, data=payload)
            self.assertEqual(r.status_code, 400)

        # Check should still have its original data:
        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")

    def test_it_rejects_six_field_cron_expression(self):
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

    def test_it_validates_tz(self):
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

    def test_it_rejects_missing_schedule(self):
        # tz field is omitted so this should fail:
        payload = {"kind": "cron", "grace": 60, "tz": "UTC"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_missing_tz(self):
        # tz field is omitted so this should fail:
        payload = {"kind": "cron", "schedule": "* * * * *", "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 400)

    def test_team_access_works(self):
        payload = {"kind": "simple", "timeout": 7200, "grace": 60}

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, data=payload)

        check = Check.objects.get(code=self.check.code)
        assert check.timeout.total_seconds() == 7200

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/timeout/"
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/timeout/"
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 404

    def test_it_checks_ownership(self):
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_allows_cross_team_access(self):
        self.bobs_profile.current_project = None
        self.bobs_profile.save()

        payload = {"kind": "simple", "timeout": 3600, "grace": 60}

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.redirect_url)
