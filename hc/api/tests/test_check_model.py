from django.test import TestCase

from hc.api.models import Check


class CheckModelTestCase(TestCase):

    def test_it_strips_tags(self):
        check = Check()

        check.tags = " foo  bar "
        self.assertEquals(check.tags_list(), ["foo", "bar"])

        check.tags = " "
        self.assertEquals(check.tags_list(), [])

    def test_in_grace_period_handles_new_check(self):
        check = Check()
        self.assertFalse(check.in_grace_period())
