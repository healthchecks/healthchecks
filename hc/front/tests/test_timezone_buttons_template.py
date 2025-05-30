from __future__ import annotations

from unittest.mock import Mock

from django.template import Context, Template
from django.test import TestCase


class TimezoneButtonsTemplateTestCase(TestCase):
    """
    Tests for time zone format buttons template rendering.
    
    Tests the template integration and HTML output for time zone deduplication functionality
    """

    def test_template_renders_buttons_correctly(self) -> None:
        """Test that the template renders all buttons with correct attributes."""
        template_content = """
        {% load hc_extras %}
        {% timezone_format_buttons check %}
        """
        
        check = Mock()
        check.kind = "cron"
        check.tz = "Asia/Jerusalem"
        
        template = Template(template_content)
        context = Context({"check": check})
        rendered = template.render(context)
        
        # Check that all buttons are rendered
        self.assertIn('data-format="Asia/Jerusalem"', rendered)
        self.assertIn('data-format="UTC"', rendered)
        self.assertIn('data-format="local"', rendered)
        
        # Check data attributes for deduplication
        self.assertIn('data-type="check"', rendered)
        self.assertIn('data-type="utc"', rendered)
        self.assertIn('data-type="browser"', rendered)
        
        # Check priority attributes
        self.assertIn('data-priority="1"', rendered)
        self.assertIn('data-priority="2"', rendered) 
        self.assertIn('data-priority="3"', rendered)
        
        # Check offset attributes (should have offset for server-side time zones)
        self.assertIn('data-offset="', rendered)  # Asia/Jerusalem and UTC should have offsets

    def test_template_renders_javascript(self) -> None:
        """Test that the JavaScript deduplication code is included."""
        template_content = """
        {% load hc_extras %}
        {% timezone_format_buttons check %}
        """
        
        check = Mock()
        check.kind = "cron"
        check.tz = "America/Los_Angeles"
        
        template = Template(template_content)
        context = Context({"check": check})
        rendered = template.render(context)
        
        # Check that JavaScript is included
        self.assertIn('<script>', rendered)
        self.assertIn('document.addEventListener', rendered)
        self.assertIn('DOMContentLoaded', rendered)
        self.assertIn('getTimezoneOffset', rendered)
        
        # Check for deduplication logic
        self.assertIn('display: none', rendered)

    def test_template_simple_check_rendering(self) -> None:
        """Test template rendering for simple checks."""
        template_content = """
        {% load hc_extras %}
        {% timezone_format_buttons check %}
        """
        
        check = Mock()
        check.kind = "simple"
        check.tz = "UTC"
        
        template = Template(template_content)
        context = Context({"check": check})
        rendered = template.render(context)
        
        # Should only have UTC and browser buttons for simple checks
        self.assertIn('data-format="UTC"', rendered)
        self.assertIn('data-format="local"', rendered)
        
        # Should not have check time zone button (since it would be duplicate of UTC)
        self.assertNotIn('data-type="check"', rendered)

    def test_template_format_switcher_structure(self) -> None:
        """Test that the format switcher has correct structure."""
        template_content = """
        {% load hc_extras %}
        {% timezone_format_buttons check %}
        """
        
        check = Mock()
        check.kind = "cron"
        check.tz = "Asia/Tokyo"
        
        template = Template(template_content)
        context = Context({"check": check})
        rendered = template.render(context)
        
        # Should have the correct structure
        self.assertIn('id="format-switcher"', rendered)
        self.assertIn('btn-group', rendered)
        self.assertIn('data-toggle="buttons"', rendered)
        self.assertIn('type="radio"', rendered)
        self.assertIn('name="date-format"', rendered)
        
        # Should initially be hidden to prevent flicker
        self.assertIn('visibility: hidden', rendered)
        
        # Should contain JavaScript to show after deduplication
        self.assertIn('formatSwitcher.style.visibility = \'visible\'', rendered)
        
        # Should contain tooltip logic for browser time zone button (just time zone name)
        self.assertIn('Intl.DateTimeFormat().resolvedOptions().timeZone', rendered)
        self.assertIn('singleBrowserTimeZone', rendered)
        
        # Should contain merged time zone tooltip logic
        self.assertIn('Represents:', rendered)
        self.assertIn('sources.join', rendered)
        self.assertIn('hasUTC', rendered)
        self.assertIn('hasCheck', rendered)
        self.assertIn('hasBrowser', rendered)