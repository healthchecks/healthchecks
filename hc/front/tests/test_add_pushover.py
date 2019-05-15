from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(
    PUSHOVER_API_TOKEN="token", PUSHOVER_SUBSCRIPTION_URL="http://example.org"
)
class AddPushoverTestCase(BaseTestCase):
    @override_settings(PUSHOVER_API_TOKEN=None)
    def test_it_requires_api_token(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/add_pushover/")
        self.assertEqual(r.status_code, 404)

    def test_instructions_work_without_login(self):
        r = self.client.get("/integrations/add_pushover/")
        self.assertContains(r, "Setup Guide")

    def test_it_shows_form(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/add_pushover/")
        self.assertContains(r, "Subscribe with Pushover")

    def test_post_redirects(self):
        self.client.login(username="alice@example.org", password="password")
        payload = {"po_priority": 2}
        r = self.client.post("/integrations/add_pushover/", form=payload)
        self.assertEqual(r.status_code, 302)

    def test_post_requires_authenticated_user(self):
        payload = {"po_priority": 2}
        r = self.client.post("/integrations/add_pushover/", form=payload)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Setup Guide")

    def test_it_adds_channel(self):
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "pushover_user_key=a&state=foo&prio=0&prio_up=-1"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        self.assertEqual(r.status_code, 302)

        channel = Channel.objects.get()
        self.assertEqual(channel.value, "a|0|-1")
        self.assertEqual(channel.project, self.project)

    def test_it_validates_priority(self):
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "pushover_user_key=a&state=foo&prio=abc"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        self.assertEqual(r.status_code, 400)

    def test_it_validates_priority_up(self):
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "pushover_user_key=a&state=foo&prio_up=abc"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        self.assertEqual(r.status_code, 400)

    def test_it_validates_state(self):
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "pushover_user_key=a&state=INVALID&prio=0"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        self.assertEqual(r.status_code, 400)
