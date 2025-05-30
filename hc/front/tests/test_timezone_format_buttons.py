from __future__ import annotations

from typing import Any
from unittest.mock import Mock

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User

from hc.front.templatetags.hc_extras import timezone_format_buttons
from hc.accounts.models import Profile


class TimezoneFormatButtonsTestCase(TestCase):
    """
    Tests for time zone format buttons functionality.
    
    This tests time zone deduplication based on current offsets with proper priority ordering.
    """
    
    def create_mock_context(self, user_preference: str | None = None) -> dict[str, Any]:
        """Helper method to create a mock context for testing."""
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_profile = Mock()
        mock_profile.default_timezone_selection = user_preference
        mock_user.profile = mock_profile
        
        mock_request = Mock()
        mock_request.user = mock_user
        
        return {'request': mock_request}

    def test_simple_check_shows_utc_and_browser(self) -> None:
        """Simple checks should show UTC and browser time zone buttons."""
        check = Mock()
        check.kind = "simple"
        check.tz = "UTC"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
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

    def test_cron_check_with_utc_timezone(self) -> None:
        """Cron check with UTC time zone should show only UTC and browser (no duplicate UTC)."""
        check = Mock()
        check.kind = "cron"
        check.tz = "UTC"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
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

    def test_cron_check_with_different_timezone(self) -> None:
        """Cron check with non-UTC time zone should show all 3 buttons."""
        check = Mock()
        check.kind = "cron"
        check.tz = "America/New_York"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
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

    def test_cron_check_with_asia_jerusalem(self) -> None:
        """Test Asia/Jerusalem time zone (DST time zone for comprehensive testing)."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Asia/Jerusalem"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
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

    def test_oncalendar_check_same_as_cron(self) -> None:
        """OnCalendar checks should behave the same as cron checks."""
        check = Mock()
        check.kind = "oncalendar"
        check.tz = "Europe/London"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
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

    def test_invalid_timezone_handling(self) -> None:
        """Invalid time zones should be handled gracefully."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Invalid/Timezone"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
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

    def test_utc_equivalent_timezone_etc_utc(self) -> None:
        """Test that Etc/UTC is handled properly."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Etc/UTC"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
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

    def test_button_data_attributes(self) -> None:
        """Test that buttons have correct data attributes for client-side processing."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Asia/Tokyo"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
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

    def test_priority_ordering(self) -> None:
        """Test that buttons are returned in correct display order with proper priorities."""
        check = Mock()
        check.kind = "cron"
        check.tz = "Pacific/Auckland"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
        buttons = result["buttons"]
        
        # Verify display order (UTC first, then check time zone, then browser)
        display_order = [button["type"] for button in buttons]
        self.assertEqual(display_order, ["utc", "check", "browser"])
        
        # Verify priorities (check=1 highest, utc=2, browser=3 lowest)
        priorities = [button["priority"] for button in buttons]
        self.assertEqual(priorities, [2, 1, 3])  # utc, check, browser

    def test_etc_gmt_plus3_vs_asia_jerusalem_not_deduplicated(self) -> None:
        """Test that Etc/GMT+3 and Asia/Jerusalem are NOT deduplicated due to opposite offsets."""
        # Etc/GMT+3 is actually GMT-3 (offset -180), not GMT+3
        # Asia/Jerusalem is GMT+2/+3 (offset +120/+180) depending on DST
        # These should NOT be deduplicated as they have opposite signs
        
        check = Mock()
        check.kind = "cron"
        check.tz = "Etc/GMT+3"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check)
        buttons = result["buttons"]
        
        self.assertEqual(len(buttons), 3)
        
        # UTC button
        utc_button = buttons[0]
        self.assertEqual(utc_button["display_name"], "UTC")
        self.assertEqual(utc_button["current_offset_minutes"], 0)
        
        # Etc/GMT+3 button - should have negative offset (GMT-3)
        check_button = buttons[1]
        self.assertEqual(check_button["display_name"], "Etc/GMT+3")
        self.assertEqual(check_button["current_offset_minutes"], -180)  # 3 hours behind UTC
        
        # Browser button (no offset in data)
        browser_button = buttons[2]
        self.assertEqual(browser_button["display_name"], "Browser's time zone")

    def test_default_button_selection(self) -> None:
        """Test that the correct button is marked as default."""
        # Simple check - UTC should be default
        check_simple = Mock()
        check_simple.kind = "simple"
        check_simple.tz = "UTC"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check_simple)
        defaults = [btn["is_default"] for btn in result["buttons"]]
        self.assertEqual(defaults, [True, False])  # UTC=True, Browser=False
        
        # Cron check - check time zone should be default (but displayed second)
        check_cron = Mock()
        check_cron.kind = "cron"
        check_cron.tz = "Asia/Tokyo"
        
        context = self.create_mock_context()
        result = timezone_format_buttons(context, check_cron)
        defaults = [btn["is_default"] for btn in result["buttons"]]
        self.assertEqual(defaults, [False, True, False])  # UTC=False, Check=True, Browser=False


class TimezonePreferenceTestCase(TestCase):
    """
    Tests for user time zone preference functionality in appearance settings.
    """
    
    def setUp(self) -> None:
        self.user = User.objects.create(username="testuser", email="test@example.com")
        self.profile = Profile.objects.for_user(self.user)

    def test_default_timezone_selection_field_default_value(self) -> None:
        """Test that default_timezone_selection defaults to 'default'."""
        self.assertEqual(self.profile.default_timezone_selection, "default")

    def test_set_timezone_preference_utc(self) -> None:
        """Test setting UTC as default time zone preference."""
        self.profile.default_timezone_selection = "utc"
        self.profile.save()
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.default_timezone_selection, "utc")

    def test_set_timezone_preference_check(self) -> None:
        """Test setting check's time zone as default preference."""
        self.profile.default_timezone_selection = "check"
        self.profile.save()
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.default_timezone_selection, "check")

    def test_set_timezone_preference_browser(self) -> None:
        """Test setting browser's time zone as default preference."""
        self.profile.default_timezone_selection = "browser"
        self.profile.save()
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.default_timezone_selection, "browser")

    def test_set_timezone_preference_default(self) -> None:
        """Test setting time zone preference back to default."""
        self.profile.default_timezone_selection = "utc"
        self.profile.save()
        
        # Now set it back to default
        self.profile.default_timezone_selection = "default"
        self.profile.save()
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.default_timezone_selection, "default")

    def test_timezone_format_buttons_respects_user_preference_utc(self) -> None:
        """Test that timezone_format_buttons respects user UTC preference."""
        # Set up user preference for UTC
        self.profile.default_timezone_selection = "utc"
        self.profile.save()
        
        # Create a check and context
        check = Mock()
        check.kind = "cron"
        check.tz = "America/New_York"
        
        # Create context with authenticated user
        mock_request = Mock()
        mock_request.user = self.user
        context = {'request': mock_request}
        
        result = timezone_format_buttons(context, check)
        
        # Verify that request is included in result for template access
        self.assertEqual(result['request'], mock_request)
        
        # Verify buttons are generated correctly
        buttons = result['buttons']
        self.assertEqual(len(buttons), 3)  # UTC, Check, Browser
        
        # UTC button should be first
        utc_button = buttons[0]
        self.assertEqual(utc_button['type'], 'utc')
        
        # Check button should be second
        check_button = buttons[1]
        self.assertEqual(check_button['type'], 'check')
        
        # Browser button should be third
        browser_button = buttons[2]
        self.assertEqual(browser_button['type'], 'browser')

    def test_timezone_format_buttons_respects_user_preference_check(self) -> None:
        """Test that timezone_format_buttons respects user check time zone preference."""
        # Set up user preference for check's time zone
        self.profile.default_timezone_selection = "check"
        self.profile.save()
        
        # Create a check and context
        check = Mock()
        check.kind = "cron"
        check.tz = "Europe/London"
        
        # Create context with authenticated user
        mock_request = Mock()
        mock_request.user = self.user
        context = {'request': mock_request}
        
        result = timezone_format_buttons(context, check)
        
        # Verify that request is included in result for template access
        self.assertEqual(result['request'], mock_request)
        self.assertEqual(result['check'], check)

    def test_timezone_format_buttons_respects_user_preference_browser(self) -> None:
        """Test that timezone_format_buttons respects user browser time zone preference."""
        # Set up user preference for browser time zone
        self.profile.default_timezone_selection = "browser"
        self.profile.save()
        
        # Create a check and context
        check = Mock()
        check.kind = "simple"
        check.tz = "UTC"
        
        # Create context with authenticated user
        mock_request = Mock()
        mock_request.user = self.user
        context = {'request': mock_request}
        
        result = timezone_format_buttons(context, check)
        
        # Verify that request is included in result for template access
        self.assertEqual(result['request'], mock_request)
        
        # For simple checks, should have UTC and Browser buttons
        buttons = result['buttons']
        self.assertEqual(len(buttons), 2)
        
        # Find browser button
        browser_button = next(btn for btn in buttons if btn['type'] == 'browser')
        self.assertEqual(browser_button['type'], 'browser')
        self.assertEqual(browser_button['display_name'], "Browser's time zone")

    def test_timezone_format_buttons_with_default_preference(self) -> None:
        """Test that timezone_format_buttons works with default preference."""
        # Keep default preference
        self.assertEqual(self.profile.default_timezone_selection, "default")
        
        # Create a check and context
        check = Mock()
        check.kind = "cron"
        check.tz = "Asia/Tokyo"
        
        # Create context with authenticated user
        mock_request = Mock()
        mock_request.user = self.user
        context = {'request': mock_request}
        
        result = timezone_format_buttons(context, check)
        
        # Verify that request is included in result for template access
        self.assertEqual(result['request'], mock_request)
        
        # Should have all 3 buttons for cron check
        buttons = result['buttons']
        self.assertEqual(len(buttons), 3)

    def test_timezone_format_buttons_with_unauthenticated_user(self) -> None:
        """Test that timezone_format_buttons works with unauthenticated user."""
        # Create context with unauthenticated user
        mock_user = Mock()
        mock_user.is_authenticated = False
        mock_request = Mock()
        mock_request.user = mock_user
        context = {'request': mock_request}
        
        # Create a check
        check = Mock()
        check.kind = "cron"
        check.tz = "UTC"
        
        result = timezone_format_buttons(context, check)
        
        # Should still work and include the request
        self.assertEqual(result['request'], mock_request)
        
        # Should have UTC and Browser buttons (UTC time zone matches check)
        buttons = result['buttons']
        self.assertEqual(len(buttons), 2)

    def test_timezone_format_buttons_context_missing_request(self) -> None:
        """Test that timezone_format_buttons handles missing request in context."""
        # Create context without request
        context: dict[str, Any] = {}
        
        # Create a check
        check = Mock()
        check.kind = "simple"
        check.tz = "UTC"
        
        result = timezone_format_buttons(context, check)
        
        # Should handle missing request gracefully
        self.assertIsNone(result['request'])
        
        # Should still generate buttons
        buttons = result['buttons']
        self.assertEqual(len(buttons), 2)  # UTC and Browser for simple check