from __future__ import annotations

from django.test import SimpleTestCase
from django.test.utils import override_settings

from hc.lib.badges import get_badge_svg, get_width


class BadgesTestCase(SimpleTestCase):
    def test_get_width_works(self) -> None:
        self.assertEqual(get_width("mm"), 20)
        # Default width for unknown characters is 7
        self.assertEqual(get_width("@"), 7)

    def test_it_makes_svg(self) -> None:
        svg = get_badge_svg("foo", "up")
        self.assertIn("#4c1", svg)

        svg = get_badge_svg("bar", "down")
        self.assertIn("#e05d44", svg)

    @override_settings(LANGUAGE_CODE="pt-br")
    def test_it_uses_decimal_dot(self) -> None:
        svg = get_badge_svg("a", "up")
        self.assertIn("8.5", svg)
        self.assertNotIn("8,5", svg)
