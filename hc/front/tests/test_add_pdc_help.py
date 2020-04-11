from django.test.utils import override_settings
from hc.test import BaseTestCase


@override_settings(PD_VENDOR_KEY="foo")
class AddPdcHelpTestCase(BaseTestCase):
    url = "/integrations/add_pdc/"

    def test_instructions_work_when_not_logged_in(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Before adding PagerDuty integration, please log")

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "If your team uses")

    @override_settings(PD_VENDOR_KEY=None)
    def test_it_requires_vendor_key(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
