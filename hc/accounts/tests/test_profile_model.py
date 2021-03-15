from datetime import timedelta as td

from django.utils.timezone import now
from hc.test import BaseTestCase
from hc.api.models import Check


class ProfileModelTestCase(BaseTestCase):
    def test_it_sets_next_nag_date(self):
        Check.objects.create(project=self.project, status="down")

        self.profile.nag_period = td(hours=1)
        self.profile.update_next_nag_date()

        self.assertTrue(self.profile.next_nag_date)

    def test_it_does_not_set_next_nag_date_if_no_nag_period(self):
        Check.objects.create(project=self.project, status="down")
        self.profile.update_next_nag_date()
        self.assertIsNone(self.profile.next_nag_date)

    def test_it_does_not_update_existing_next_nag_date(self):
        Check.objects.create(project=self.project, status="down")

        original_nag_date = now() - td(minutes=30)

        self.profile.next_nag_date = original_nag_date
        self.profile.nag_period = td(hours=1)
        self.profile.update_next_nag_date()

        self.assertEqual(self.profile.next_nag_date, original_nag_date)

    def test_it_clears_next_nag_date(self):
        self.profile.next_nag_date = now()
        self.profile.update_next_nag_date()
        self.assertIsNone(self.profile.next_nag_date)
