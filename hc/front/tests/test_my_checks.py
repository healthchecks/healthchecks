from hc.api.models import Check
from hc.test import BaseTestCase
from datetime import timedelta as td
from django.utils import timezone


class MyChecksTestCase(BaseTestCase):

    def setUp(self):
        super(MyChecksTestCase, self).setUp()
        self.check = Check(user=self.alice, name="Alice Was Here")
        self.check.save()

    def test_it_works(self):
        for email in ("alice@example.org", "bob@example.org"):
            self.client.login(username=email, password="password")
            r = self.client.get("/checks/")
            self.assertContains(r, "Alice Was Here", status_code=200)

    def test_it_shows_green_check(self):
        self.check.last_ping = timezone.now()
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/")
        self.assertContains(r, "icon-up")

    def test_it_shows_red_check(self):
        self.check.last_ping = timezone.now() - td(days=3)
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/")
        self.assertContains(r, "icon-down")

    def test_it_shows_amber_check(self):
        self.check.last_ping = timezone.now() - td(days=1, minutes=30)
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/")
        self.assertContains(r, "icon-grace")

    def test_it_hides_add_check_button(self):
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/")
        self.assertContains(r, "Check limit reached", status_code=200)

    def test_it_saves_sort_field(self):
        self.client.login(username="alice@example.org", password="password")
        self.client.get("/checks/?sort=name")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sort, "name")

    def test_it_ignores_bad_sort_value(self):
        self.client.login(username="alice@example.org", password="password")
        self.client.get("/checks/?sort=invalid")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sort, "created")

    def test_it_shows_started_but_down_badge(self):
        self.check.last_start = timezone.now()
        self.check.tags = "foo"
        self.check.status = "down"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/")
        self.assertContains(r, """<div class="btn btn-xs down ">foo</div>""")

    def test_it_shows_grace_badge(self):
        self.check.last_ping = timezone.now() - td(days=1, minutes=10)
        self.check.tags = "foo"
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/")
        self.assertContains(r, """<div class="btn btn-xs grace ">foo</div>""")

    def test_it_shows_grace_started_badge(self):
        self.check.last_start = timezone.now()
        self.check.last_ping = timezone.now() - td(days=1, minutes=10)
        self.check.tags = "foo"
        self.check.status = "up"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/")
        self.assertContains(r, """<div class="btn btn-xs grace ">foo</div>""")
