from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(
    PUSHOVER_API_TOKEN="token", PUSHOVER_SUBSCRIPTION_URL="http://example.org"
)
class AddPushoverTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_pushover/"

    @override_settings(PUSHOVER_API_TOKEN=None)
    def test_it_requires_api_token(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Subscribe with Pushover")

    def test_post_redirects(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        payload = {"po_priority": 2, "po_priority_up": 0}
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 302)

        target = r.headers["Location"]
        params = parse_qs(urlparse(target).query)

        success_url = params["success"][0]
        sparams = parse_qs(urlparse(success_url).query)
        self.assertEqual(sparams["prio"][0], "2")
        self.assertEqual(sparams["prio_up"][0], "0")

    def test_it_requires_authenticated_user(self) -> None:
        r = self.client.get(self.url)
        self.assertRedirects(r, "/accounts/login/?next=" + self.url)

    def test_it_adds_channel(self) -> None:
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

    def test_it_handles_prio_disabled(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "?pushover_user_key=a&state=foo&prio=-3&prio_up=-3"
        r = self.client.get(self.url + params, follow=True)
        self.assertRedirects(r, self.channels_url)

        channel = Channel.objects.get()
        self.assertEqual(channel.value, "a|-3|-3")
        self.assertEqual(channel.project, self.project)

    def test_it_validates_priority(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "?pushover_user_key=a&state=foo&prio=abc"
        r = self.client.get(self.url + params)
        self.assertEqual(r.status_code, 400)

    def test_it_validates_priority_up(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "?pushover_user_key=a&state=foo&prio_up=abc"
        r = self.client.get(self.url + params)
        self.assertEqual(r.status_code, 400)

    def test_it_validates_state(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        session = self.client.session
        session["pushover"] = "foo"
        session.save()

        params = "?pushover_user_key=a&state=INVALID&prio=0"
        r = self.client.get(self.url + params)
        self.assertEqual(r.status_code, 403)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
