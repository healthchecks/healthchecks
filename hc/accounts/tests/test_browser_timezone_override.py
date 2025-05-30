from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase

from hc.accounts.models import Profile
from hc.lib.tz import get_effective_browser_timezone


class BrowserTimezoneOverrideTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user("alice@example.org", password="password")
        self.profile = Profile.objects.for_user(self.user)

    def test_browser_timezone_override_default_empty(self) -> None:
        """Test that browser_timezone_override defaults to empty string."""
        self.assertEqual(self.profile.browser_timezone_override, "")

    def test_get_effective_browser_timezone_no_override(self) -> None:
        """Test get_effective_browser_timezone returns browser time zone when no override."""
        browser_tz = "America/New_York"
        effective_tz = get_effective_browser_timezone(self.profile, browser_tz)
        self.assertEqual(effective_tz, browser_tz)

    def test_get_effective_browser_timezone_with_override(self) -> None:
        """Test get_effective_browser_timezone returns override when set."""
        self.profile.browser_timezone_override = "Europe/London"
        self.profile.save()
        
        browser_tz = "America/New_York"
        effective_tz = get_effective_browser_timezone(self.profile, browser_tz)
        self.assertEqual(effective_tz, "Europe/London")

    def test_get_effective_browser_timezone_fallback_to_none(self) -> None:
        """Test get_effective_browser_timezone returns None when no browser time zone."""
        effective_tz = get_effective_browser_timezone(self.profile, None)
        self.assertEqual(effective_tz, None)

    def test_get_effective_browser_timezone_override_takes_precedence(self) -> None:
        """Test that override takes precedence even when browser time zone is None."""
        self.profile.browser_timezone_override = "Asia/Tokyo"
        self.profile.save()
        
        effective_tz = get_effective_browser_timezone(self.profile, None)
        self.assertEqual(effective_tz, "Asia/Tokyo")

    def test_get_effective_browser_timezone_with_none_profile(self) -> None:
        """Test get_effective_browser_timezone handles None profile gracefully."""
        effective_tz = get_effective_browser_timezone(None, "America/Chicago")
        self.assertEqual(effective_tz, "America/Chicago")

    def test_get_effective_browser_timezone_with_none_profile_and_browser_tz(self) -> None:
        """Test get_effective_browser_timezone returns None with None profile and browser_tz."""
        effective_tz = get_effective_browser_timezone(None, None)
        self.assertEqual(effective_tz, None)


class AppearanceViewTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user("alice@example.org", password="password")
        self.profile = Profile.objects.for_user(self.user)

    def test_appearance_view_get(self) -> None:
        """Test that appearance view loads successfully."""
        self.client.force_login(self.user)
        r = self.client.get("/accounts/profile/appearance/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Browser Time Zone Override")

    def test_browser_timezone_override_post_valid(self) -> None:
        """Test setting a valid browser time zone override."""
        self.client.force_login(self.user)
        
        r = self.client.post("/accounts/profile/appearance/", {
            "browser_timezone_override": "Europe/London"
        })
        
        self.assertEqual(r.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.browser_timezone_override, "Europe/London")
        self.assertContains(r, "Your settings have been updated!")

    def test_browser_timezone_override_post_empty(self) -> None:
        """Test setting browser time zone override to empty (default)."""
        # First set a value
        self.profile.browser_timezone_override = "Asia/Tokyo"
        self.profile.save()
        
        self.client.force_login(self.user)
        
        r = self.client.post("/accounts/profile/appearance/", {
            "browser_timezone_override": ""
        })
        
        self.assertEqual(r.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.browser_timezone_override, "")
        self.assertContains(r, "Your settings have been updated!")

    def test_browser_timezone_override_post_invalid(self) -> None:
        """Test setting an invalid browser time zone override."""
        self.client.force_login(self.user)
        
        r = self.client.post("/accounts/profile/appearance/", {
            "browser_timezone_override": "Invalid/Timezone"
        })
        
        self.assertEqual(r.status_code, 200)
        self.profile.refresh_from_db()
        # Should remain unchanged
        self.assertEqual(self.profile.browser_timezone_override, "")
        # Should not show success message
        self.assertNotContains(r, "Your settings have been updated!")

    def test_browser_timezone_override_context(self) -> None:
        """Test that appearance view provides correct context for browser time zone override."""
        self.client.force_login(self.user)
        r = self.client.get("/accounts/profile/appearance/")
        
        self.assertEqual(r.status_code, 200)
        self.assertIn("all_timezones", r.context)
        self.assertIn("browser_tz_status", r.context)
        self.assertEqual(r.context["browser_tz_status"], "default")

    def test_multiple_form_submissions_independent(self) -> None:
        """Test that different form submissions don't interfere with each other."""
        self.client.force_login(self.user)
        
        # Submit theme form
        r = self.client.post("/accounts/profile/appearance/", {
            "theme": "dark"
        })
        self.assertEqual(r.status_code, 200)
        
        # Submit time zone override form
        r = self.client.post("/accounts/profile/appearance/", {
            "browser_timezone_override": "Europe/Berlin"
        })
        self.assertEqual(r.status_code, 200)
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.theme, "dark")
        self.assertEqual(self.profile.browser_timezone_override, "Europe/Berlin")