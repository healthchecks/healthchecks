from django.test import TestCase

from hc.lib.string import replace


class StringTestCase(TestCase):
    def test_it_works(self):
        result = replace("$A is $B", {"$A": "aaa", "$B": "bbb"})
        self.assertEqual(result, "aaa is bbb")

    def test_it_ignores_placeholders_in_values(self):
        result = replace("$A is $B", {"$A": "$B", "$B": "$A"})
        self.assertEqual(result, "$B is $A")

    def test_it_ignores_overlapping_placeholders(self):
        result = replace("$$AB", {"$A": "", "$B": "text"})
        self.assertEqual(result, "$B")

    def test_it_preserves_non_placeholder_dollar_signs(self):
        result = replace("$3.50", {"$A": "text"})
        self.assertEqual(result, "$3.50")
