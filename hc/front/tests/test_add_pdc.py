from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(PD_VENDOR_KEY="foo")
class AddPdConnectTestCase(BaseTestCase):
    def setUp(self):
        super(AddPdConnectTestCase, self).setUp()
        self.url = "/projects/%s/add_pdc/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "If your team uses")

    def test_it_works(self):
        session = self.client.session
        session["pd"] = "1234567890AB"  # 12 characters
        session.save()

        self.client.login(username="alice@example.org", password="password")
        url = self.url + "1234567890AB/?service_key=123"
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "pd")
        self.assertEqual(c.pd_service_key, "123")
        self.assertEqual(c.project, self.project)

    def test_it_validates_code(self):
        session = self.client.session
        session["pd"] = "1234567890AB"
        session.save()

        self.client.login(username="alice@example.org", password="password")
        url = self.url + "XXXXXXXXXXXX/?service_key=123"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

    @override_settings(PD_VENDOR_KEY=None)
    def test_it_requires_vendor_key(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
