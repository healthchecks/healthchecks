from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(PD_VENDOR_KEY="foo")
class AddPdConnectTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = "/projects/%s/add_pdc/" % self.project.code

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

    @override_settings(PD_VENDOR_KEY=None)
    def test_it_requires_vendor_key(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
