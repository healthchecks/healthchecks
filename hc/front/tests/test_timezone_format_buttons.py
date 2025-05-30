from __future__ import annotations

from unittest.mock import Mock

from django.test import TestCase

from hc.front.templatetags.hc_extras import timezone_format_buttons


class TimezoneFormatButtonsTestCase(TestCase):
    """
    Tests for time zone format buttons functionality.
    
    This tests time zone deduplication based on current offsets with proper priority ordering.
    """

    def test_simple_check_shows_utc_and_browser(self):
        """Simple checks should show UTC and browser time zone buttons."""
        check = Mock()
        check.kind = "simple"
        check.tz = "UTC"
        
        result = timezone_format_buttons(check)
        buttons = result["buttons"]
        
        self.assertEqual(len(buttons), 2)
        
        # Check UTC button
        utc_button = buttons[0]
        self.assertEqual(utc_button["display_name"], "UTC")
        self.assertEqual(utc_button["type"], "utc")
        self.assertEqual(utc_button["priority"], 2)
        self.assertEqual(utc_button["current_offset_minutes"], 0)
        self.assertTrue(utc_button["is_default"])
        
        # Check browser button
        browser_button = buttons[1]
        self.assertEqual(browser_button["display_name"], "Browser's time zone")
        self.assertEqual(browser_button["type"], "browser")
        self.assertEqual(browser_button["priority"], 3)
        self.assertFalse(browser_button["is_default"])

    def test_cron_check_with_utc_timezone(self):
        """Cron check with UTC time zone should show only UTC and browser (no duplicate UTC)."""
        check = Mock()
        check.kind = "cron"
        check.tz = "UTC"
        
        result = timezone_format_buttons(check)
        buttons = result["buttons"]
        
        self.assertEqual(len(buttons), 2)
        
        # Check UTC button (from check time zone)
        utc_button = buttons[0]
        self.assertEqual(utc_button["display_name"], "UTC")
        self.assertEqual(utc_button["type"], "check")
        self.assertEqual(utc_button["priority"], 1)
        self.assertEqual(utc_button["current_offset_minutes"], 0)
        self.assertTrue(utc_button["is_default"])
        
        # Check browser button
        browser_button = buttons[1]
        self.assertEqual(browser_button["display_name"], "Browser's time zone")
        self.assertEqual(browser_button["type"], "browser")
        self.assertEqual(browser_button["priority"], 3)

    def test_cron_check_with_different_timezone(self):
        """Cron check with non-UTC time zone should show all 3 buttons."""
        check = Mock()
        check.kind = "cron"
        check.tz = "America/New_York"
        
        result = timezone_format_buttons(check)
        buttons = result["buttons"]
        
        self.assertEqual(len(buttons), 3)
        
        # UTC button (now first)
        utc_button = buttons[0]
        self.assertEqual(utc_button["display_name"], "UTC")
        self.assertEqual(utc_button["type"], "utc")
        self.assertEqual(utc_button["priority"], 2)
        self.assertEqual(utc_button["current_offset_minutes"], 0)
        self.assertFalse(utc_button["is_default"])
        
        # Check time zone button (now second)
        check_button = buttons[1]
        self.assertEqual(check_button["display_name"], "America/New_York")
        self.assertEqual(check_button["type"], "check")
        self.assertEqual(check_button["priority"], 1)
        self.assertTrue(check_button["is_default"])
        # EST is UTC-5 (-300 minutes) or EDT is UTC-4 (-240 minutes)
        self.assertIn(check_button["current_offset_minutes"], [-300, -240])
        
        # Browser button (still third)
        browser_button = buttons[2]
        self.assertEqual(browser_button["display_name"], "Browser's time zone")
        self.assertEqual(browser_button["type"], "browser")
        self.assertEqual(browser_button["priority"], 3)

    def test_cron_check_with_asia_jerusalem(self):
        """Test Asia/Jerusalem time zone (DST time zone for comprehensive testing)."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Asia/Jerusalem"
        
        result = timezone_format_buttons(check)
        buttons = result["buttons"]
        
        self.assertEqual(len(buttons), 3)
        
        # UTC button (now first)
        utc_button = buttons[0]
        self.assertEqual(utc_button["display_name"], "UTC")
        self.assertEqual(utc_button["type"], "utc")
        self.assertEqual(utc_button["priority"], 2)
        
        # Check time zone button (now second)
        check_button = buttons[1]
        self.assertEqual(check_button["display_name"], "Asia/Jerusalem")
        self.assertEqual(check_button["type"], "check")
        self.assertEqual(check_button["priority"], 1)
        self.assertTrue(check_button["is_default"])
        # Israel Standard Time (UTC+2) or Israel Daylight Time (UTC+3)
        self.assertIn(check_button["current_offset_minutes"], [120, 180])

    def test_oncalendar_check_same_as_cron(self):
        """OnCalendar checks should behave the same as cron checks."""
        check = Mock()
        check.kind = "oncalendar"
        check.tz = "Europe/London"
        
        result = timezone_format_buttons(check)
        buttons = result["buttons"]
        
        self.assertEqual(len(buttons), 3)
        
        # UTC button (now first)
        utc_button = buttons[0]
        self.assertEqual(utc_button["display_name"], "UTC")
        self.assertEqual(utc_button["type"], "utc")
        self.assertEqual(utc_button["priority"], 2)
        
        # Check time zone button (now second, but still has the highest priority for deduplication)
        check_button = buttons[1]
        self.assertEqual(check_button["display_name"], "Europe/London")
        self.assertEqual(check_button["type"], "check")
        self.assertEqual(check_button["priority"], 1)
        self.assertTrue(check_button["is_default"])

    def test_invalid_timezone_handling(self):
        """Invalid time zones should be handled gracefully."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Invalid/Timezone"
        
        result = timezone_format_buttons(check)
        buttons = result["buttons"]
        
        self.assertEqual(len(buttons), 3)
        
        # UTC button (now first)
        utc_button = buttons[0]
        self.assertEqual(utc_button["display_name"], "UTC")
        self.assertEqual(utc_button["type"], "utc")
        
        # Check button (now second) should still be created with 0 offset fallback
        check_button = buttons[1]
        self.assertEqual(check_button["display_name"], "Invalid/Timezone")
        self.assertEqual(check_button["type"], "check")
        self.assertEqual(check_button["current_offset_minutes"], 0)

    def test_utc_equivalent_timezone_etc_utc(self):
        """Test that Etc/UTC is handled properly."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Etc/UTC"
        
        result = timezone_format_buttons(check)
        buttons = result["buttons"]
        
        self.assertEqual(len(buttons), 3)
        
        # UTC button should be first
        utc_button = buttons[0]
        self.assertEqual(utc_button["display_name"], "UTC")
        self.assertEqual(utc_button["type"], "utc")
        self.assertEqual(utc_button["current_offset_minutes"], 0)
        
        # Check time zone button should be second
        check_button = buttons[1]
        self.assertEqual(check_button["display_name"], "Etc/UTC")
        self.assertEqual(check_button["type"], "check")
        self.assertEqual(check_button["current_offset_minutes"], 0)
        
        # Both have same offset (0) - client-side JS should deduplicate

    def test_button_data_attributes(self):
        """Test that buttons have correct data attributes for client-side processing."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Asia/Tokyo"
        
        result = timezone_format_buttons(check)
        buttons = result["buttons"]
        
        # UTC button should be first
        utc_button = buttons[0]
        self.assertEqual(utc_button["data_format"], "UTC")
        self.assertEqual(utc_button["current_offset_minutes"], 0)
        
        # Check time zone button should be second
        check_button = buttons[1]
        self.assertEqual(check_button["data_format"], "Asia/Tokyo")
        self.assertIsInstance(check_button["current_offset_minutes"], int)
        
        # Browser button should be third
        browser_button = buttons[2]
        self.assertEqual(browser_button["data_format"], "local")
        self.assertNotIn("current_offset_minutes", browser_button)

    def test_priority_ordering(self):
        """Test that buttons are returned in correct display order with proper priorities."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Pacific/Auckland"
        
        result = timezone_format_buttons(check)
        buttons = result["buttons"]
        
        # Verify display order (UTC first, then check time zone, then browser)
        display_order = [button["type"] for button in buttons]
        self.assertEqual(display_order, ["utc", "check", "browser"])
        
        # Verify priorities (check=1 highest, utc=2, browser=3 lowest)
        priorities = [button["priority"] for button in buttons]
        self.assertEqual(priorities, [2, 1, 3])  # utc, check, browser

    def test_default_button_selection(self):
        """Test that the correct button is marked as default."""
        # Simple check - UTC should be default
        check_simple = Mock()
        check_simple.kind = "simple"
        check_simple.tz = "UTC"
        
        result = timezone_format_buttons(check_simple)
        defaults = [btn["is_default"] for btn in result["buttons"]]
        self.assertEqual(defaults, [True, False])  # UTC=True, Browser=False
        
        # Cron check - check time zone should be default (but displayed second)
        check_cron = Mock()
        check_cron.kind = "cron"
        check_cron.tz = "Asia/Tokyo"
        
        result = timezone_format_buttons(check_cron)
        defaults = [btn["is_default"] for btn in result["buttons"]]
        self.assertEqual(defaults, [False, True, False])  # UTC=False, Check=True, Browser=False