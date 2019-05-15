from datetime import timedelta as td

from django.conf import settings
from django.core.signing import base64_hmac
from django.utils.timezone import now

from hc.api.models import Check
from hc.test import BaseTestCase


class BadgeTestCase(BaseTestCase):
    def setUp(self):
        super(BadgeTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project, tags="foo bar")

        sig = base64_hmac(str(self.project.badge_key), "foo", settings.SECRET_KEY)
        sig = sig[:8]
        self.svg_url = "/badge/%s/%s/foo.svg" % (self.project.badge_key, sig)
        self.json_url = "/badge/%s/%s/foo.json" % (self.project.badge_key, sig)

    def test_it_rejects_bad_signature(self):
        r = self.client.get("/badge/%s/12345678/foo.svg" % self.project.badge_key)
        assert r.status_code == 404

    def test_it_returns_svg(self):
        r = self.client.get(self.svg_url)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")
        self.assertContains(r, "#4c1")

    def test_it_handles_options(self):
        r = self.client.options(self.svg_url)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

    def test_it_handles_new(self):
        r = self.client.get(self.json_url)
        doc = r.json()
        self.assertEqual(doc["status"], "up")
        self.assertEqual(doc["total"], 1)
        self.assertEqual(doc["grace"], 0)
        self.assertEqual(doc["down"], 0)

    def test_it_handles_started_but_down(self):
        self.check.last_start = now()
        self.check.tags = "foo"
        self.check.status = "down"
        self.check.save()

        r = self.client.get(self.json_url)
        doc = r.json()
        self.assertEqual(doc["status"], "down")
        self.assertEqual(doc["total"], 1)
        self.assertEqual(doc["grace"], 0)
        self.assertEqual(doc["down"], 1)

    def test_it_shows_grace_badge(self):
        self.check.last_ping = now() - td(days=1, minutes=10)
        self.check.tags = "foo"
        self.check.status = "up"
        self.check.save()

        r = self.client.get(self.json_url)
        doc = r.json()
        self.assertEqual(doc["status"], "late")
        self.assertEqual(doc["total"], 1)
        self.assertEqual(doc["grace"], 1)
        self.assertEqual(doc["down"], 0)

    def test_it_shows_started_but_grace_badge(self):
        self.check.last_start = now()
        self.check.last_ping = now() - td(days=1, minutes=10)
        self.check.tags = "foo"
        self.check.status = "up"
        self.check.save()

        r = self.client.get(self.json_url)
        doc = r.json()
        self.assertEqual(doc["status"], "late")
        self.assertEqual(doc["total"], 1)
        self.assertEqual(doc["grace"], 1)
        self.assertEqual(doc["down"], 0)

    def test_it_handles_special_characters(self):
        self.check.tags = "db@dc1"
        self.check.save()

        sig = base64_hmac(str(self.project.badge_key), "db@dc1", settings.SECRET_KEY)
        sig = sig[:8]
        url = "/badge/%s/%s/db%%2540dc1.svg" % (self.project.badge_key, sig)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
