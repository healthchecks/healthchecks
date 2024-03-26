from __future__ import annotations

from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from unittest.mock import Mock, patch

from django.test.utils import override_settings

from hc.api.models import Check, Flip, Ping
from hc.test import BaseTestCase


class DetailsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project, name="Foo")

        ping = Ping.objects.create(owner=self.check)

        # Older MySQL versions don't store microseconds. This makes sure
        # the ping is older than any notifications we may create later:
        ping.created = "2000-01-01T00:00:00+00:00"
        ping.save()

        self.url = f"/checks/{self.check.code}/details/"

    @override_settings(SITE_NAME="Mychecks")
    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "How To Ping", status_code=200)
        self.assertContains(r, "ping-now")
        # The page should contain timezone strings
        self.assertContains(r, "Europe/Riga")

        self.assertContains(r, "Foo – Mychecks", status_code=200)
        self.assertContains(r, "favicon.svg")

    def test_it_suggests_tags_from_other_checks(self) -> None:
        self.check.tags = "foo bar"
        self.check.save()

        Check.objects.create(project=self.project, tags="baz")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "bar baz foo", status_code=200)

    def test_it_checks_ownership(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_cron_expression(self) -> None:
        self.check.kind = "cron"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Cron Expression", status_code=200)

    def test_it_allows_cross_team_access(self) -> None:
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_hides_actions_from_readonly_users(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)

        self.assertNotContains(r, "edit-name", status_code=200)
        self.assertNotContains(r, "edit-desc")
        self.assertNotContains(r, "Filtering Rules")
        self.assertNotContains(r, "pause-btn")
        self.assertNotContains(r, "Change Schedule")
        self.assertNotContains(r, "Create a Copy&hellip;")
        self.assertNotContains(r, "transfer-btn")
        self.assertNotContains(r, "btn-remove")

    def test_it_hides_resume_action_from_readonly_users(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.check.status = "paused"
        self.check.manual_resume = True
        self.check.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)

        self.assertNotContains(r, "resume-btn", status_code=200)

    def test_crontab_example_guesses_schedules(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        pairs = [
            (td(minutes=1), "* * * * *"),
            (td(minutes=12), "*/12 * * * *"),
            (td(hours=1), "0 * * * *"),
            (td(hours=6), "0 */6 * * *"),
            (td(days=1), "0 0 * * *"),
        ]

        for timeout, expression in pairs:
            self.check.timeout = timeout
            self.check.save()

            r = self.client.get(self.url)
            self.assertContains(r, f"{expression} /your/command.sh")
            self.assertNotContains(r, 'FIXME: replace "* * * * *"')

    def test_crontab_example_handles_unsupported_timeout_values(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        self.check.timeout = td(minutes=13)
        self.check.save()

        r = self.client.get(self.url)
        self.assertContains(r, "* * * * * /your/command.sh")
        self.assertContains(r, 'FIXME: replace "* * * * *"')

    @patch("hc.lib.date.now")
    def test_it_calculates_downtime_summary(self, mock_now: Mock) -> None:
        mock_now.return_value = datetime(2020, 2, 1, tzinfo=timezone.utc)

        self.check.created = datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.check.save()

        # going down on Jan 15, at 12:00
        f1 = Flip(owner=self.check)
        f1.created = datetime(2020, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        f1.old_status = "up"
        f1.new_status = "down"
        f1.save()

        # back up on Jan 15, at 13:00
        f2 = Flip(owner=self.check)
        f2.created = datetime(2020, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        f2.old_status = "down"
        f2.new_status = "up"
        f2.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Feb. 2020")
        self.assertContains(r, "Jan. 2020")
        self.assertContains(r, "Dec. 2019")

        # The summary for Jan. 2020 should be "1 downtime, 1 hour total"
        self.assertContains(r, "1 downtime, 1 h 0 min total")
        self.assertContains(r, "99.86% uptime")

    @patch("hc.lib.date.now")
    def test_it_downtime_summary_handles_plural(self, mock_now: Mock) -> None:
        mock_now.return_value = datetime(2020, 2, 1, tzinfo=timezone.utc)

        self.check.created = datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.check.save()

        # going down on Jan 15, at 12:00
        f1 = Flip(owner=self.check)
        f1.created = datetime(2020, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        f1.old_status = "up"
        f1.new_status = "down"
        f1.save()

        # back up 2 hours later
        f2 = Flip(owner=self.check)
        f2.created = datetime(2020, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        f2.old_status = "down"
        f2.new_status = "up"
        f2.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertContains(r, "1 downtime, 2 h 0 min total")
        self.assertContains(r, "99.73% uptime")

    @patch("hc.lib.date.now")
    def test_downtime_summary_handles_positive_utc_offset(self, mock_now: Mock) -> None:
        mock_now.return_value = datetime(2020, 2, 1, tzinfo=timezone.utc)

        self.profile.tz = "America/New_York"
        self.profile.save()

        self.check.created = datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        # It is not February yet in America/New_York:
        self.assertNotContains(r, "Feb. 2020")
        self.assertContains(r, "Jan. 2020")
        self.assertContains(r, "Dec. 2019")
        self.assertContains(r, "Nov. 2019")

    @patch("hc.lib.date.now")
    def test_downtime_summary_handles_negative_utc_offset(self, mock_now: Mock) -> None:
        mock_now.return_value = datetime(2020, 1, 31, 23, tzinfo=timezone.utc)

        self.profile.tz = "Europe/Riga"
        self.profile.save()

        self.check.created = datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        # It is February already in Europe/Riga:
        self.assertContains(r, "Feb. 2020")
        self.assertContains(r, "Jan. 2020")
        self.assertContains(r, "Dec. 2019")

    @patch("hc.lib.date.now")
    def test_it_handles_months_when_check_did_not_exist(self, mock_now: Mock) -> None:
        mock_now.return_value = datetime(2020, 2, 1, tzinfo=timezone.utc)

        self.check.created = datetime(2020, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Feb. 2020")
        self.assertContains(r, "Jan. 2020")
        self.assertContains(r, "Dec. 2019")

        # The summary for Dec. 2019 should be "–"
        self.assertContains(r, "<td>–</td>", html=True)

    def test_it_handles_no_ping_key(self) -> None:
        self.project.show_slugs = True
        self.project.ping_key = None
        self.project.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Ping Key Required", status_code=200)
        self.assertNotContains(r, "ping-now")

    def test_it_handles_no_ping_key_for_readonly_user(self) -> None:
        self.project.show_slugs = True
        self.project.ping_key = None
        self.project.save()

        self.bobs_membership.role = "r"
        self.bobs_membership.save()
        self.client.login(username="bob@example.org", password="password")

        r = self.client.get(self.url)
        self.assertNotContains(r, "Ping Key Required", status_code=200)
        self.assertNotContains(r, "ping-now")

    def test_it_handles_empty_slug(self) -> None:
        self.project.show_slugs = True
        self.project.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "(unavailable, set name first)", status_code=200)
        self.assertNotContains(r, "Copy URL")
        self.assertNotContains(r, "ping-now")

    def test_it_saves_url_format_preference(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.client.get(self.url + "?urls=slug")

        self.project.refresh_from_db()
        self.assertTrue(self.project.show_slugs)

    def test_it_outputs_period_grace_as_integers(self) -> None:
        self.check.timeout = td(seconds=123)
        self.check.grace = td(seconds=456)
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertContains(r, 'data-timeout="123"')
        self.assertContains(r, 'data-grace="456"')

    @override_settings(SITE_NAME="Mychecks")
    def test_it_sets_title_and_favicon(self) -> None:
        self.check.status = "down"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "DOWN – Foo – Mychecks", status_code=200)
        self.assertContains(r, "favicon_down.svg")
