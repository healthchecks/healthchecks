from hc.api.models import Check
from hc.test import BaseTestCase


class UpdateNameTestCase(BaseTestCase):

    def setUp(self):
        super(UpdateNameTestCase, self).setUp()
        self.check = Check(user=self.alice)
        self.check.save()

    def test_it_works(self):
        url = "/checks/%s/name/" % self.check.code
        payload = {"name": "Alice Was Here"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        self.assertRedirects(r, "/checks/")

        check = Check.objects.get(code=self.check.code)
        assert check.name == "Alice Was Here"

    def test_team_access_works(self):
        url = "/checks/%s/name/" % self.check.code
        payload = {"name": "Bob Was Here"}

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(url, data=payload)

        check = Check.objects.get(code=self.check.code)
        assert check.name == "Bob Was Here"

    def test_it_checks_ownership(self):
        url = "/checks/%s/name/" % self.check.code
        payload = {"name": "Charlie Sent This"}

        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 403

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/name/"
        payload = {"name": "Alice Was Here"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 400

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/name/"
        payload = {"name": "Alice Was Here"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 404

    def test_it_sanitizes_tags(self):
        url = "/checks/%s/name/" % self.check.code
        payload = {"tags": "  foo  bar\r\t \n  baz \n"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(url, data=payload)

        check = Check.objects.get(id=self.check.id)
        self.assertEqual(check.tags, "foo bar baz")

    def test_it_rejects_get(self):
        url = "/checks/%s/name/" % self.check.code
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 405)
