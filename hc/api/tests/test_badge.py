from django.conf import settings
from django.core.signing import base64_hmac

from hc.api.models import Check
from hc.test import BaseTestCase


class BadgeTestCase(BaseTestCase):

    def setUp(self):
        super(BadgeTestCase, self).setUp()
        self.check = Check.objects.create(user=self.alice, tags="foo bar")

    def test_it_rejects_bad_signature(self):
        r = self.client.get("/badge/%s/12345678/foo.svg" % self.alice.username)
        assert r.status_code == 404

    def test_it_returns_svg(self):
        sig = base64_hmac(str(self.alice.username), "foo", settings.SECRET_KEY)
        sig = sig[:8]
        url = "/badge/%s/%s/foo.svg" % (self.alice.username, sig)

        r = self.client.get(url)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")
        self.assertContains(r, "#4c1")

    def test_it_handles_options(self):
        sig = base64_hmac(str(self.alice.username), "foo", settings.SECRET_KEY)
        sig = sig[:8]
        url = "/badge/%s/%s/foo.svg" % (self.alice.username, sig)

        r = self.client.options(url)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")
