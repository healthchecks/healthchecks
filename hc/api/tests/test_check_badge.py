from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Check
from hc.test import BaseTestCase


class CheckBadgeTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project, name="foobar")
        badge_key = self.check.prepare_badge_key()

        self.svg_url = f"/b/2/{badge_key}.svg"
        self.json_url = f"/b/2/{badge_key}.json"
        self.with_late_url = f"/b/3/{badge_key}.json"
        self.shields_url = f"/b/2/{badge_key}.shields"

    def test_it_handles_bad_badge_key(self) -> None:
        r = self.client.get("/b/2/869fe06a-a604-4140-b15a-118637c25f3e.svg")
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
            {
                "schemaVersion": 1,
                "label": "foobar",
                "message": "up",
                "color": "success",
            },
        )
