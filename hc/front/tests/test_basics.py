from django.test import TestCase
from django.test.utils import override_settings


class BasicsTestCase(TestCase):
    def test_it_shows_welcome(self):
        r = self.client.get("/")
        self.assertContains(r, "Get Notified", status_code=200)
        self.assertNotContains(r, "do not use in production")

    @override_settings(DEBUG=True)
    def test_it_shows_debug_warning(self):
        r = self.client.get("/")
        self.assertContains(r, "do not use in production")

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_obeys_registration_open(self):
        r = self.client.get("/")

        self.assertNotContains(r, "Get Started")
