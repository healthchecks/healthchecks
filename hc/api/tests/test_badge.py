from __future__ import annotations

from datetime import timedelta as td

from django.conf import settings
from django.core.signing import base64_hmac
from django.utils.timezone import now

from hc.api.models import Check
from hc.test import BaseTestCase


class BadgeTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project, tags="foo bar")

        sig = base64_hmac(str(self.project.badge_key), "foo", settings.SECRET_KEY)
        sig = sig[:8]

        self.svg_url = "/badge/%s/%s-2/foo.svg" % (self.project.badge_key, sig)
        self.json_url = "/badge/%s/%s-2/foo.json" % (self.project.badge_key, sig)
        self.with_late_url = "/badge/%s/%s/foo.json" % (self.project.badge_key, sig)
        self.shields_url = "/badge/%s/%s-2/foo.shields" % (self.project.badge_key, sig)

    def test_it_rejects_bad_signature(self) -> None:
        r = self.client.get("/badge/%s/12345678/foo.svg" % self.project.badge_key)
        self.assertEqual(r.status_code, 404)

    def test_it_returns_svg(self) -> None:
        r = self.client.get(self.svg_url)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")
        self.assertIn("no-cache", r["Cache-Control"])
        self.assertContains(r, "#4c1")

    def test_it_rejects_bad_format(self) -> None:
        r = self.client.get(self.json_url + "foo")
        self.assertEqual(r.status_code, 404)

    def test_it_handles_options(self) -> None:
        r = self.client.options(self.svg_url)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

    def test_it_handles_new(self) -> None:
        doc = self.client.get(self.json_url).json()
        self.assertEqual(doc, {"status": "up", "total": 1, "grace": 0, "down": 0})

    def test_it_ignores_started_when_down(self) -> None:
        self.check.last_start = now()
        self.check.status = "down"
        self.check.save()

        doc = self.client.get(self.json_url).json()
        self.assertEqual(doc, {"status": "down", "total": 1, "grace": 0, "down": 1})

    def test_it_treats_late_as_up(self) -> None:
        self.check.last_ping = now() - td(days=1, minutes=10)
        self.check.status = "up"
        self.check.save()

        doc = self.client.get(self.json_url).json()
        self.assertEqual(doc, {"status": "up", "total": 1, "grace": 1, "down": 0})

    def test_it_handles_special_characters(self) -> None:
        self.check.tags = "db@dc1"
        self.check.save()

        sig = base64_hmac(str(self.project.badge_key), "db@dc1", settings.SECRET_KEY)
        sig = sig[:8]
        url = "/badge/%s/%s/db%%2540dc1.svg" % (self.project.badge_key, sig)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_late_mode_returns_late_status(self) -> None:
        self.check.last_ping = now() - td(days=1, minutes=10)
        self.check.status = "up"
        self.check.save()

        doc = self.client.get(self.with_late_url).json()
        self.assertEqual(doc, {"status": "late", "total": 1, "grace": 1, "down": 0})

    def test_late_mode_ignores_started_when_late(self) -> None:
        self.check.last_start = now()
        self.check.last_ping = now() - td(days=1, minutes=10)
        self.check.status = "up"
        self.check.save()

        doc = self.client.get(self.with_late_url).json()
        self.assertEqual(doc, {"status": "late", "total": 1, "grace": 1, "down": 0})

    def test_it_returns_shields_json(self) -> None:
        doc = self.client.get(self.shields_url).json()
        self.assertEqual(
            doc,
            {"schemaVersion": 1, "label": "foo", "message": "up", "color": "success"},
        )
