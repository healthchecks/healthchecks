from hc.api.models import Check
from hc.test import BaseTestCase
from datetime import timedelta as td
from django.utils import timezone


class MyChecksTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check(project=self.project, name="Alice Was Here")
        self.check.save()

        self.url = "/projects/%s/checks/" % self.project.code

    def test_it_works(self):
        for email in ("alice@example.org", "bob@example.org"):
            self.client.login(username=email, password="password")
            r = self.client.get(self.url)
            self.assertContains(r, "Alice Was Here", status_code=200)
            # The pause button:
            self.assertContains(r, "btn btn-default pause", status_code=200)

        # last_active_date should have been set
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.last_active_date)

    def test_it_bumps_last_active_date(self):
        self.profile.last_active_date = timezone.now() - td(days=10)
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.get(self.url)

        # last_active_date should have been bumped
        self.profile.refresh_from_db()
        delta = timezone.now() - self.profile.last_active_date
        self.assertTrue(delta.total_seconds() < 1)

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
        self.check.last_ping = timezone.now()
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "ic-up")

    def test_it_shows_red_check(self):
        self.check.last_ping = timezone.now() - td(days=3)
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "ic-down")

    def test_it_shows_amber_check(self):
        self.check.last_ping = timezone.now() - td(days=1, minutes=30)
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "ic-grace")

    def test_it_hides_add_check_button(self):
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Check limit reached", status_code=200)

    def test_it_saves_sort_field(self):
        self.client.login(username="alice@example.org", password="password")
        self.client.get(self.url + "?sort=name")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sort, "name")

    def test_it_ignores_bad_sort_value(self):
        self.client.login(username="alice@example.org", password="password")
        self.client.get(self.url + "?sort=invalid")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sort, "created")

    def test_it_shows_started_but_down_badge(self):
        self.check.last_start = timezone.now()
        self.check.tags = "foo"
        self.check.status = "down"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, """<div class="btn btn-xs down ">foo</div>""")

    def test_it_shows_grace_badge(self):
        self.check.last_ping = timezone.now() - td(days=1, minutes=10)
        self.check.tags = "foo"
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, """<div class="btn btn-xs grace ">foo</div>""")

    def test_it_shows_grace_started_badge(self):
        self.check.last_start = timezone.now()
        self.check.last_ping = timezone.now() - td(days=1, minutes=10)
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

        self.assertNotContains(r, "Add Check", status_code=200)

        # The pause button:
        self.assertNotContains(r, "btn btn-default pause", status_code=200)
