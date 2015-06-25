from django.test import TestCase


class BasicsTestCase(TestCase):

    def test_it_shows_welcome(self):
        r = self.client.get("/")
        self.assertContains(r, "Welcome", status_code=200)
