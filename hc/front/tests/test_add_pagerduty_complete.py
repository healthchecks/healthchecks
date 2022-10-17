from __future__ import annotations

import json
from urllib.parse import urlencode

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(PD_APP_ID="FOOBAR")
class AddPagerDutyCompleteTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        session = self.client.session
        session["pagerduty"] = ("ABC", str(self.project.code))
        session.save()

    def _url(self, state="ABC"):
        config = {
            "account": {"name": "Foo"},
            "integration_keys": [{"integration_key": "foo", "name": "bar"}],
        }

        url = "/integrations/add_pagerduty/?"
        url += urlencode({"state": state, "config": json.dumps(config)})
        return url

    def test_it_adds_channel(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self._url())
        self.assertRedirects(r, self.channels_url)

        channel = Channel.objects.get()
        self.assertEqual(channel.kind, "pd")
        self.assertEqual(channel.pd_service_key, "foo")
        self.assertEqual(channel.pd_account, "Foo")

    def test_it_validates_state(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self._url(state="XYZ"))
        self.assertEqual(r.status_code, 403)

    @override_settings(PD_APP_ID=None)
    def test_it_requires_app_id(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 404)

    @override_settings(PD_ENABLED=False)
    def test_it_requires_pd_enabled(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self):
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 403)
