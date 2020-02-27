from django.test.utils import override_settings
from hc.test import BaseTestCase


@override_settings(PD_VENDOR_KEY="foo")
class AddPdcCompleteTestCase(BaseTestCase):
    def setUp(self):
        super(AddPdcCompleteTestCase, self).setUp()
        self.url = "/projects/%s/add_pdc/" % self.project.code
        self.url += "XXXXXXXXXXXX/?service_key=123"

    def test_it_validates_code(self):
        session = self.client.session
        session["pd"] = "1234567890AB"
        session.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 400)

    @override_settings(PD_VENDOR_KEY=None)
    def test_it_requires_vendor_key(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
