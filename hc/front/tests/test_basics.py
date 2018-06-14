from django.test import TestCase
from django.test.utils import override_settings

from hc.api.models import Check


class BasicsTestCase(TestCase):

    def test_it_shows_welcome(self):
        r = self.client.get("/")
        self.assertContains(r, "Get Notified", status_code=200)

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_obeys_registration_open(self):
        r = self.client.get("/")

        self.assertNotContains(r, "Get Started")
