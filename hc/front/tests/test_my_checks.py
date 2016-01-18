from hc.api.models import Check
from hc.test import BaseTestCase


class MyChecksTestCase(BaseTestCase):

    def setUp(self):
        super(MyChecksTestCase, self).setUp()
        self.check = Check(user=self.alice, name="Alice Was Here")
        self.check.save()

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/")
        self.assertContains(r, "Alice Was Here", status_code=200)
