from datetime import timedelta as td
import uuid

from django.utils.timezone import now
from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class UpdateCheckTestCase(BaseTestCase):
    def setUp(self):
        super(UpdateCheckTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project)

    def post(self, code, data):
        url = "/api/v1/checks/%s" % code
        return self.client.post(url, data, content_type="application/json")

    def test_it_works(self):
        self.check.last_ping = now()
        self.check.status = "up"
        self.check.save()

        r = self.post(
            self.check.code,
            {
                "api_key": "X" * 32,
                "name": "Foo",
                "tags": "bar,baz",
                "desc": "My description",
                "timeout": 3600,
                "grace": 60,
            },
        )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        assert "ping_url" in doc
        self.assertEqual(doc["name"], "Foo")
        self.assertEqual(doc["tags"], "bar,baz")
        self.assertEqual(doc["desc"], "My description")
        self.assertEqual(doc["n_pings"], 0)

        self.assertTrue("schedule" not in doc)
        self.assertTrue("tz" not in doc)

        self.assertEqual(Check.objects.count(), 1)

        self.check.refresh_from_db()
        self.assertEqual(self.check.name, "Foo")
        self.assertEqual(self.check.tags, "bar,baz")
        self.assertEqual(self.check.timeout.total_seconds(), 3600)
        self.assertEqual(self.check.grace.total_seconds(), 60)

        # alert_after should be updated too
        expected_aa = self.check.last_ping + td(seconds=3600 + 60)
        self.assertEqual(self.check.alert_after, expected_aa)

    def test_it_handles_options(self):
        r = self.client.options("/api/v1/checks/%s" % self.check.code)
        self.assertEqual(r.status_code, 204)
        self.assertIn("POST", r["Access-Control-Allow-Methods"])

    def test_it_unassigns_channels(self):
        Channel.objects.create(project=self.project)
        self.check.assign_all_channels()

        r = self.post(self.check.code, {"api_key": "X" * 32, "channels": ""})

        self.assertEqual(r.status_code, 200)
        check = Check.objects.get()
        self.assertEqual(check.channel_set.count(), 0)

    def test_it_handles_invalid_uuid(self):
        r = self.post("not-an-uuid", {"api_key": "X" * 32})
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_check(self):
        made_up_code = "07c2f548-9850-4b27-af5d-6c9dc157ec02"
        r = self.post(made_up_code, {"api_key": "X" * 32})
        self.assertEqual(r.status_code, 404)

    def test_it_validates_ownership(self):
        check = Check.objects.create(project=self.bobs_project, status="up")

        r = self.post(check.code, {"api_key": "X" * 32})
        self.assertEqual(r.status_code, 403)

    def test_it_updates_cron_to_simple(self):
        self.check.kind = "cron"
        self.check.schedule = "5 * * * *"
        self.check.save()

        r = self.post(self.check.code, {"api_key": "X" * 32, "timeout": 3600})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")

    def test_it_sets_single_channel(self):
        channel = Channel.objects.create(project=self.project)
        # Create another channel so we can test that only the first one
        # gets assigned:
        Channel.objects.create(project=self.project)

        r = self.post(
            self.check.code, {"api_key": "X" * 32, "channels": str(channel.code)}
        )

        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 1)
        self.assertEqual(self.check.channel_set.first().code, channel.code)

    def test_it_sets_the_channel_only_once(self):
        channel = Channel.objects.create(project=self.project)
        duplicates = "%s,%s" % (channel.code, channel.code)
        r = self.post(self.check.code, {"api_key": "X" * 32, "channels": duplicates})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 1)

    def test_it_handles_comma_separated_channel_codes(self):
        c1 = Channel.objects.create(project=self.project)
        c2 = Channel.objects.create(project=self.project)
        r = self.post(
            self.check.code,
            {"api_key": "X" * 32, "channels": "%s,%s" % (c1.code, c2.code)},
        )

        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 2)

    def test_it_handles_asterix(self):
        Channel.objects.create(project=self.project)
        Channel.objects.create(project=self.project)
        r = self.post(self.check.code, {"api_key": "X" * 32, "channels": "*"})

        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 2)

    def test_it_ignores_channels_if_channels_key_missing(self):
        Channel.objects.create(project=self.project)
        self.check.assign_all_channels()

        r = self.post(self.check.code, {"api_key": "X" * 32})
        self.assertEqual(r.status_code, 200)
        check = Check.objects.get()
        self.assertEqual(check.channel_set.count(), 1)

    def test_it_rejects_bad_channel_code(self):
        payload = {"api_key": "X" * 32, "channels": "abc", "name": "New Name"}
        r = self.post(self.check.code, payload,)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid channel identifier: abc")

        # The name should be unchanged
        self.check.refresh_from_db()
        self.assertEqual(self.check.name, "")

    def test_it_rejects_missing_channel(self):
        code = str(uuid.uuid4())
        r = self.post(self.check.code, {"api_key": "X" * 32, "channels": code})

        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid channel identifier: " + code)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 0)

    def test_it_rejects_channel_from_another_project(self):
        charlies_channel = Channel.objects.create(project=self.charlies_project)

        code = str(charlies_channel.code)
        r = self.post(self.check.code, {"api_key": "X" * 32, "channels": code})

        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid channel identifier: " + code)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 0)

    def test_it_rejects_non_uuid_channel_code(self):
        r = self.post(self.check.code, {"api_key": "X" * 32, "channels": "foo"})

        self.assertEqual(r.status_code, 400)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 0)

    def test_it_rejects_non_string_channels_key(self):
        r = self.post(self.check.code, {"api_key": "X" * 32, "channels": None})

        self.assertEqual(r.status_code, 400)

    def test_it_rejects_non_string_desc(self):
        r = self.post(self.check.code, {"api_key": "X" * 32, "desc": 123})

        self.assertEqual(r.status_code, 400)

    def test_it_validates_cron_expression(self):
        self.check.kind = "cron"
        self.check.schedule = "5 * * * *"
        self.check.save()

        samples = ["* invalid *", "1,2 3,* * * *", "0 0 31 2 *"]
        for sample in samples:
            r = self.post(self.check.code, {"api_key": "X" * 32, "schedule": sample})
            self.assertEqual(r.status_code, 400, "Did not reject '%s'" % sample)

        # Schedule should be unchanged
        self.check.refresh_from_db()
        self.assertEqual(self.check.schedule, "5 * * * *")

    def test_it_rejects_readonly_key(self):
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.post(self.check.code, {"api_key": "R" * 32, "name": "Foo"})
        self.assertEqual(r.status_code, 401)
