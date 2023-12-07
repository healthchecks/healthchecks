from __future__ import annotations

import uuid
from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Channel, Check
from hc.lib.typealias import JSONDict
from hc.test import BaseTestCase, TestHttpResponse


class UpdateCheckTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)

    def post(
        self,
        code: uuid.UUID | str,
        data: JSONDict,
        v: int = 1,
        api_key: str = "X" * 32,
    ) -> TestHttpResponse:
        url = f"/api/v{v}/checks/{code}"
        return self.csrf_client.post(
            url, data, content_type="application/json", HTTP_X_API_KEY=api_key
        )

    def test_it_works(self) -> None:
        self.check.last_ping = now()
        self.check.status = "up"
        self.check.save()

        r = self.post(
            self.check.code,
            {
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
        self.assertEqual(doc["slug"], "foo")
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

    def test_it_handles_options(self) -> None:
        r = self.client.options("/api/v1/checks/%s" % self.check.code)
        self.assertEqual(r.status_code, 204)
        self.assertIn("POST", r["Access-Control-Allow-Methods"])

    def test_it_unassigns_channels(self) -> None:
        Channel.objects.create(project=self.project)
        self.check.assign_all_channels()

        r = self.post(self.check.code, {"channels": ""})
        self.assertEqual(r.status_code, 200)

        check = Check.objects.get()
        self.assertEqual(check.channel_set.count(), 0)

    def test_it_handles_invalid_uuid(self) -> None:
        r = self.post("not-an-uuid", {})
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_check(self) -> None:
        made_up_code = "07c2f548-9850-4b27-af5d-6c9dc157ec02"
        r = self.post(made_up_code, {})
        self.assertEqual(r.status_code, 404)

    def test_it_validates_ownership(self) -> None:
        check = Check.objects.create(project=self.bobs_project, status="up")

        r = self.post(check.code, {})
        self.assertEqual(r.status_code, 403)

    def test_it_updates_cron_to_simple(self) -> None:
        self.check.kind = "cron"
        self.check.schedule = "5 * * * *"
        self.check.save()

        r = self.post(self.check.code, {"timeout": 3600})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "simple")

    def test_it_updates_cron_to_oncalendar(self) -> None:
        self.check.kind = "cron"
        self.check.schedule = "5 * * * *"
        self.check.save()

        r = self.post(self.check.code, {"schedule": "12:34"})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.kind, "oncalendar")
        self.assertEqual(self.check.schedule, "12:34")

    def test_it_sets_single_channel(self) -> None:
        channel = Channel.objects.create(project=self.project)
        # Create another channel so we can test that only the first one
        # gets assigned:
        Channel.objects.create(project=self.project)

        r = self.post(self.check.code, {"channels": str(channel.code)})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 1)
        self.assertEqual(self.check.channel_set.get().code, channel.code)

    def test_it_sets_the_channel_only_once(self) -> None:
        channel = Channel.objects.create(project=self.project)
        duplicates = f"{channel.code},{channel.code}"
        r = self.post(self.check.code, {"channels": duplicates})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 1)

    def test_it_sets_channel_by_name(self) -> None:
        channel = Channel.objects.create(project=self.project, name="alerts")

        r = self.post(self.check.code, {"channels": "alerts"})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 1)
        self.assertEqual(self.check.channel_set.get().code, channel.code)

    def test_it_sets_channel_by_name_formatted_as_uuid(self) -> None:
        name = "102eaa82-a274-4b15-a499-c1bb6bbcd7b6"
        channel = Channel.objects.create(project=self.project, name=name)

        r = self.post(self.check.code, {"channels": name})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 1)
        self.assertEqual(self.check.channel_set.get().code, channel.code)

    def test_it_handles_comma_separated_channel_codes(self) -> None:
        c1 = Channel.objects.create(project=self.project)
        c2 = Channel.objects.create(project=self.project)
        r = self.post(self.check.code, {"channels": "%s,%s" % (c1.code, c2.code)})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 2)

    def test_it_handles_asterix(self) -> None:
        Channel.objects.create(project=self.project)
        Channel.objects.create(project=self.project)
        r = self.post(self.check.code, {"channels": "*"})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 2)

    def test_it_ignores_channels_if_channels_key_missing(self) -> None:
        Channel.objects.create(project=self.project)
        self.check.assign_all_channels()

        r = self.post(self.check.code, {})
        self.assertEqual(r.status_code, 200)

        check = Check.objects.get()
        self.assertEqual(check.channel_set.count(), 1)

    def test_it_rejects_bad_channel_code(self) -> None:
        r = self.post(self.check.code, {"channels": "abc", "name": "New Name"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid channel identifier: abc")

        # The name should be unchanged
        self.check.refresh_from_db()
        self.assertEqual(self.check.name, "")

    def test_it_rejects_missing_channel(self) -> None:
        code = str(uuid.uuid4())
        r = self.post(self.check.code, {"channels": code})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid channel identifier: " + code)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 0)

    def test_it_rejects_channel_from_another_project(self) -> None:
        charlies_channel = Channel.objects.create(project=self.charlies_project)
        code = str(charlies_channel.code)

        r = self.post(self.check.code, {"channels": code})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid channel identifier: " + code)

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 0)

    def test_it_handles_channel_lookup_by_name_with_no_results(self) -> None:
        r = self.post(self.check.code, {"channels": "foo"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid channel identifier: foo")

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 0)

    def test_it_handles_channel_lookup_by_name_with_multiple_results(self) -> None:
        Channel.objects.create(project=self.project, name="foo")
        Channel.objects.create(project=self.project, name="foo")

        r = self.post(self.check.code, {"channels": "foo"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "non-unique channel identifier: foo")

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 0)

    def test_it_rejects_multiple_empty_channel_names(self) -> None:
        Channel.objects.create(project=self.project, name="")

        r = self.post(self.check.code, {"channels": ","})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "empty channel identifier")

        self.check.refresh_from_db()
        self.assertEqual(self.check.channel_set.count(), 0)

    def test_it_rejects_non_string_channels_key(self) -> None:
        r = self.post(self.check.code, {"channels": 123})
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_non_string_desc(self) -> None:
        r = self.post(self.check.code, {"desc": 123})
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_null_values(self) -> None:
        for field in [
            "channels",
            "timeout",
            "grace",
            "name",
            "schedule",
            "subject",
            "subject_fail",
            "unique",
        ]:
            r = self.post(self.check.code, {field: None})
            self.assertEqual(r.status_code, 400)

    def test_it_validates_schedule(self) -> None:
        self.check.kind = "cron"
        self.check.schedule = "5 * * * *"
        self.check.save()

        cron_samples = ["* invalid *", "1,2 61 * * *", "0 0 31 2 *"]
        oncalendar_samples = ["Surprise 12:34", "12:34 Europe/surprise"]
        for sample in cron_samples + oncalendar_samples:
            r = self.post(self.check.code, {"schedule": sample})
            self.assertEqual(r.status_code, 400, f"Did not reject '{sample}'")

        # Schedule should be unchanged
        self.check.refresh_from_db()
        self.assertEqual(self.check.schedule, "5 * * * *")

    def test_it_rejects_readonly_key(self) -> None:
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.post(self.check.code, {"name": "Foo"}, api_key="R" * 32)
        self.assertEqual(r.status_code, 401)

    def test_it_sets_manual_resume_to_true(self) -> None:
        r = self.post(self.check.code, {"manual_resume": True})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.manual_resume)

    def test_it_sets_manual_resume_to_false(self) -> None:
        self.check.manual_resume = True
        self.check.save()

        r = self.post(self.check.code, {"manual_resume": False})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertFalse(self.check.manual_resume)

    def test_it_sets_methods(self) -> None:
        r = self.post(self.check.code, {"methods": "POST"})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.methods, "POST")

    def test_it_clears_methods(self) -> None:
        self.check.methods = "POST"
        self.check.save()

        # Client supplies an empty string: we should save it
        r = self.post(self.check.code, {"methods": ""})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.methods, "")

    def test_it_leaves_methods_unchanged(self) -> None:
        self.check.methods = "POST"
        self.check.save()

        # Client omits the methods key: we should leave it unchanged
        r = self.post(self.check.code, {})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.methods, "POST")

    def test_it_rejects_bad_methods_value(self) -> None:
        r = self.post(self.check.code, {"methods": "bad-value"})
        self.assertEqual(r.status_code, 400)

    def test_it_sets_success_kw(self) -> None:
        r = self.post(self.check.code, {"subject": "SUCCESS,COMPLETE"})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.filter_subject)
        self.assertEqual(self.check.success_kw, "SUCCESS,COMPLETE")

    def test_it_sets_failure_kw(self) -> None:
        r = self.post(self.check.code, {"subject_fail": "FAILED,FAILURE"})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.filter_subject)
        self.assertEqual(self.check.failure_kw, "FAILED,FAILURE")

    def test_it_unsets_filter_subject_flag(self) -> None:
        self.check.filter_subject = True
        self.check.success_kw = "SUCCESS"
        self.check.save()

        r = self.post(self.check.code, {"subject": ""})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertFalse(self.check.filter_subject)
        self.assertEqual(self.check.success_kw, "")

    def test_it_accepts_60_days_timeout(self) -> None:
        r = self.post(self.check.code, {"timeout": 60 * 24 * 3600})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.timeout.total_seconds(), 60 * 24 * 3600)

    def test_it_rejects_out_of_range_timeout(self) -> None:
        r = self.post(self.check.code, {"timeout": 500 * 24 * 3600})
        self.assertEqual(r.status_code, 400)

    def test_it_prioritizes_filter_subject_field(self) -> None:
        r = self.post(self.check.code, {"subject": "SUCCESS", "filter_subject": False})
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertFalse(self.check.filter_subject)
        self.assertEqual(self.check.success_kw, "SUCCESS")

    def test_v1_reports_status_started(self) -> None:
        self.check.last_start = now()
        self.check.save()

        r = self.post(self.check.code, {})
        doc = r.json()
        self.assertEqual(doc["status"], "started")
        self.assertTrue(doc["started"])

    def test_v2_reports_started_separately(self) -> None:
        self.check.last_start = now()
        self.check.save()

        r = self.post(self.check.code, {}, v=2)
        doc = r.json()
        self.assertEqual(doc["status"], "new")
        self.assertTrue(doc["started"])

    def test_v3_saves_slug(self) -> None:
        r = self.post(self.check.code, {"slug": "updated-slug"}, v=3)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.slug, "updated-slug")

    def test_v3_does_not_autogenerate_slug(self) -> None:
        self.check.slug = "foo"
        self.check.save()

        r = self.post(self.check.code, {"name": "Bar"}, v=3)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.slug, "foo")
