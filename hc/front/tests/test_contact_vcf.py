from __future__ import annotations

from django.test.utils import override_settings
from hc.test import BaseTestCase


class ContactVcfTestCase(BaseTestCase):
    @override_settings(SITE_NAME="MyChecks")
    def test_it_works(self) -> None:
        r = self.client.get("/contact.vcf")
        self.assertEqual(r.headers["Content-Type"], "text/vcard")
        self.assertContains(r, "MyChecks delivers voice and SMS")
