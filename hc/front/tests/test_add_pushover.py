from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(
    PUSHOVER_API_TOKEN="token", PUSHOVER_SUBSCRIPTION_URL="http://example.org"
)
class AddPushoverTestCase(BaseTestCase):
    def setUp(self):
        super(AddPushoverTestCase, self).setUp()
        self.url = "/projects/%s/add_pushover/" % self.project.code

    @override_settings(PUSHOVER_API_TOKEN=None)
    def test_it_requires_api_token(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_form(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Subscribe with Pushover")

    def test_post_redirects(self):
        self.client.login(username="alice@example.org", password="password")
        payload = {"po_priority": 2}
        r = self.client.post(self.url, form=payload)
        self.assertEqual(r.status_code, 302)

    def test_it_requires_authenticated_user(self):
        r = self.client.get(self.url)
        self.assertRedirects(r, "/accounts/login/?next=" + self.url)

    def test_it_adds_channel(self):
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "?pushover_user_key=a&state=foo&prio=0&prio_up=-1"
        r = self.client.get(self.url + params, follow=True)
        self.assertRedirects(r, self.channels_url)

        channel = Channel.objects.get()
        self.assertEqual(channel.value, "a|0|-1")
        self.assertEqual(channel.project, self.project)

    def test_it_validates_priority(self):
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "?pushover_user_key=a&state=foo&prio=abc"
        r = self.client.get(self.url + params)
        self.assertEqual(r.status_code, 400)

    def test_it_validates_priority_up(self):
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "?pushover_user_key=a&state=foo&prio_up=abc"
        r = self.client.get(self.url + params)
        self.assertEqual(r.status_code, 400)

    def test_it_validates_state(self):
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "?pushover_user_key=a&state=INVALID&prio=0"
        r = self.client.get(self.url + params)
        self.assertEqual(r.status_code, 403)
