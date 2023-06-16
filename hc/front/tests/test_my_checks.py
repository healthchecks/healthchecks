from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Check
from hc.test import BaseTestCase


class MyChecksTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check(project=self.project, name="Alice Was Here")
        self.check.slug = "alice-was-here"
        self.check.save()

        self.url = f"/projects/{self.project.code}/checks/"

    def test_it_works(self):
        for email in ("alice@example.org", "bob@example.org"):
            self.client.login(username=email, password="password")
            r = self.client.get(self.url)
            self.assertContains(r, "Alice Was Here", status_code=200)
            self.assertContains(r, str(self.check.code), status_code=200)
            # The pause button:
            self.assertContains(r, "btn pause", status_code=200)

        # last_active_date should have been set
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.last_active_date)

    def test_it_bumps_last_active_date(self):
        self.profile.last_active_date = now() - td(days=10)
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.get(self.url)

        # last_active_date should have been bumped
        self.profile.refresh_from_db()
        duration = now() - self.profile.last_active_date
        self.assertTrue(duration.total_seconds() < 1)

    def test_it_updates_session(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.assertEqual(self.client.session["last_project_id"], self.project.id)

    def test_it_checks_access(self):
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_green_check(self):
        self.check.last_ping = now()
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "ic-up")

    def test_it_shows_red_check(self):
        self.check.last_ping = now() - td(days=3)
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "ic-down")

    def test_it_shows_amber_check(self):
        self.check.last_ping = now() - td(days=1, minutes=30)
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "ic-grace")

    def test_it_hides_add_check_button(self):
        self.profile.check_limit = 1
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "There are more things to monitor", status_code=200)

    def test_it_saves_sort_field(self):
        self.client.login(username="alice@example.org", password="password")
        self.client.get(self.url + "?sort=name")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sort, "name")

    def test_it_includes_filters_in_sort_urls(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?tag=foo&search=bar")
        self.assertContains(r, "?tag=foo&search=bar&sort=name")
        self.assertContains(r, "?tag=foo&search=bar&sort=last_ping")

    def test_it_ignores_bad_sort_value(self):
        self.client.login(username="alice@example.org", password="password")
        self.client.get(self.url + "?sort=invalid")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sort, "created")

    def test_it_shows_started_but_down_badge(self):
        self.check.last_start = now()
        self.check.tags = "foo"
        self.check.status = "down"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, """<div class="btn btn-xs down ">foo</div>""")

    def test_it_shows_grace_badge(self):
        self.check.last_ping = now() - td(days=1, minutes=10)
        self.check.tags = "foo"
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, """<div class="btn btn-xs grace ">foo</div>""")

    def test_it_shows_grace_started_badge(self):
        self.check.last_start = now()
        self.check.last_ping = now() - td(days=1, minutes=10)
        self.check.tags = "foo"
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, """<div class="btn btn-xs grace ">foo</div>""")

    def test_it_hides_actions_from_readonly_users(self):
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)

        self.assertNotContains(r, 'data-target="#add-check-modal"', status_code=200)

        # The pause button:
        self.assertNotContains(r, "btn btn-default pause", status_code=200)

    def test_it_shows_slugs(self):
        self.project.show_slugs = True
        self.project.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "alice-was-here")
        self.assertNotContains(r, "(not unique)")

    def test_it_shows_not_unique_note(self):
        self.project.show_slugs = True
        self.project.save()

        dupe = Check(project=self.project, name="Alice Was Here")
        dupe.slug = "alice-was-here"
        dupe.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "alice-was-here")
        self.assertContains(r, "(not unique)")

    def test_it_saves_url_format_preference(self):
        self.client.login(username="alice@example.org", password="password")
        self.client.get(self.url + "?urls=slug")

        self.project.refresh_from_db()
        self.assertTrue(self.project.show_slugs)

    def test_it_outputs_period_grace_as_integers(self):
        self.check.timeout = td(seconds=123)
        self.check.grace = td(seconds=456)
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertContains(r, 'data-timeout="123"')
        self.assertContains(r, 'data-grace="456"')
