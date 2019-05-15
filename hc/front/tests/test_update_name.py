from hc.api.models import Check
from hc.test import BaseTestCase


class UpdateNameTestCase(BaseTestCase):
    def setUp(self):
        super(UpdateNameTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project)

        self.url = "/checks/%s/name/" % self.check.code
        self.redirect_url = "/projects/%s/checks/" % self.project.code

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data={"name": "Alice Was Here"})
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.name, "Alice Was Here")

    def test_team_access_works(self):
        payload = {"name": "Bob Was Here"}

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, data=payload)

        self.check.refresh_from_db()
        self.assertEqual(self.check.name, "Bob Was Here")

    def test_it_allows_cross_team_access(self):
        # Bob's current profile is not set
        self.bobs_profile.current_project = None
        self.bobs_profile.save()

        # But this should still work:
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, data={"name": "Bob Was Here"})
        self.assertRedirects(r, self.redirect_url)

    def test_it_checks_ownership(self):
        payload = {"name": "Charlie Sent This"}

        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/name/"
        payload = {"name": "Alice Was Here"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/name/"
        payload = {"name": "Alice Was Here"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        self.assertEqual(r.status_code, 404)

    def test_it_sanitizes_tags(self):
        payload = {"tags": "  foo  bar\r\t \n  baz \n"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, data=payload)

        self.check.refresh_from_db()
        self.assertEqual(self.check.tags, "foo bar baz")

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
