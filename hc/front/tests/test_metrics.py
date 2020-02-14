from hc.api.models import Check
from hc.test import BaseTestCase


class MetricsTestCase(BaseTestCase):
    def setUp(self):
        super(MetricsTestCase, self).setUp()
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        self.check = Check(project=self.project, name="Alice Was Here")
        self.check.tags = "foo"
        self.check.save()

        key = "R" * 32
        self.url = "/projects/%s/checks/metrics/?api_key=%s" % (self.project.code, key)

    def test_it_works(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="Alice Was Here"')
        self.assertContains(r, 'tags="foo"')
        self.assertContains(r, 'tag="foo"')
        self.assertContains(r, "hc_checks_total 1")

    def test_it_escapes_newline(self):
        self.check.name = "Line 1\nLine2"
        self.check.tags = "A\\C"
        self.check.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Line 1\\nLine2")
        self.assertContains(r, "A\\\\C")

    def test_it_checks_api_key_length(self):
        r = self.client.get(self.url + "R")
        self.assertEqual(r.status_code, 400)

    def test_it_checks_api_key(self):
        url = "/projects/%s/checks/metrics/?api_key=%s" % (self.project.code, "X" * 32)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)
