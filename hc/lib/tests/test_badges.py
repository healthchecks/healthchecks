from django.test import TestCase

from hc.lib.badges import get_width, get_badge_svg


class BadgesTestCase(TestCase):
    def test_get_width_works(self):
        self.assertEqual(get_width("mm"), 20)
        # Default width for unknown characters is 7
        self.assertEqual(get_width("@"), 7)

    def test_it_makes_svg(self):
        svg = get_badge_svg("foo", "up")
        self.assertTrue("#4c1" in svg)

        svg = get_badge_svg("bar", "down")
        self.assertTrue("#e05d44" in svg)
