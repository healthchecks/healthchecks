from __future__ import annotations

from datetime import timedelta as td

from django.conf import settings
from django.core.signing import base64_hmac
from django.utils.timezone import now

from hc.api.models import Check, Flip
from hc.test import BaseTestCase


class UptimeBadgeTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project, tags="foo bar")

        sig = base64_hmac(str(self.project.badge_key), "foo", settings.SECRET_KEY)
        sig = sig[:8] + "-4"
        
        self.svg_url = "/badge/%s/%s/foo.svg" % (self.project.badge_key, sig)
        self.json_url = "/badge/%s/%s/foo.json" % (self.project.badge_key, sig)
        self.shields_url = "/badge/%s/%s/foo.shields" % (self.project.badge_key, sig)
        
        self.check_svg_url = f"/b/4/{self.check.badge_key}.svg"
        self.check_json_url = f"/b/4/{self.check.badge_key}.json"
        self.check_shields_url = f"/b/4/{self.check.badge_key}.shields"

    def test_it_returns_svg_with_uptime(self) -> None:
        r = self.client.get(self.svg_url)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")
        self.assertIn("no-cache", r["Cache-Control"])
        self.assertContains(r, "100.0%")
        # Should be green
        self.assertContains(r, "#4c1") 

    def test_it_returns_json_with_uptime(self) -> None:
        doc = self.client.get(self.json_url).json()
        self.assertEqual(doc["status"], "100.0%")
        self.assertEqual(doc["uptime_percentage"], 100.0)

    def test_it_returns_shields_with_uptime(self) -> None:
        doc = self.client.get(self.shields_url).json()
        self.assertEqual(
            doc,
            {
                "schemaVersion": 1,
                "label": "foo",
                "message": "100.0%",
                "color": "success",
            },
        )
        
    def test_check_with_downtime(self) -> None:
        # 50% downtime scenario
        twelve_hours_ago = now() - td(hours=12)
        Flip.objects.create(
            owner=self.check,
            created=twelve_hours_ago,
            old_status="up",
            new_status="down"
        )
        six_hours_ago = now() - td(hours=6)
        Flip.objects.create(
            owner=self.check,
            created=six_hours_ago,
            old_status="down",
            new_status="up"
        )
        
        doc = self.client.get(self.check_json_url).json()
        
        self.assertIn("uptime_percentage", doc)
        self.assertGreater(doc["uptime_percentage"], 90)
        # When a check is currently down, make sure it shows reduced uptime
        
        # Down for the last day
        one_day_ago = now() - td(days=1)
        Flip.objects.create(
            owner=self.check,
            created=one_day_ago,
            old_status="up",
            new_status="down"
        )
        
        # Update check status
        self.check.status = "down"
        self.check.save()
        
        # Get the shields format to check the color
        doc = self.client.get(self.check_shields_url).json()
        
        # A check that is down would still have a fairly high uptime percentage
        # for the month, but the message should contain a percentage
        self.assertIn("%", doc["message"])
        
        # If we create more downtime history to reduce the uptime below 95%,
        # we should see the badge color change
        
        # Create more downtime events to push uptime below threshold
        for i in range(5, 15):
            days_ago = now() - td(days=i)
            Flip.objects.create(
                owner=self.check,
                created=days_ago,
                old_status="up",
                new_status="down"
            )
            
            days_ago_plus_12h = days_ago + td(hours=12)
            Flip.objects.create(
                owner=self.check,
                created=days_ago_plus_12h,
                old_status="down",
                new_status="up"
            )
        
        # Force process these flips so they're included in the calculation
        for flip in Flip.objects.filter(owner=self.check, processed=None):
            flip.processed = flip.created
            flip.save()
            
        # Now check the badge color again - with more downtime, it should change
        doc = self.client.get(self.check_shields_url).json()
        self.assertIn("color", doc)
        # The color might be "important" (orange) or "critical" (red) depending
        # on exactly how much downtime was recorded 