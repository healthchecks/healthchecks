from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class CreateCheckTestCase(BaseTestCase):
    URL = "/api/v1/checks/"

    def post(self, data, expect_fragment=None, v=1):
        if "api_key" not in data:
            data["api_key"] = "X" * 32

        url = f"/api/v{v}/checks/"
        r = self.csrf_client.post(url, data, content_type="application/json")
        if expect_fragment:
            self.assertEqual(r.status_code, 400)
            self.assertIn(expect_fragment, r.json()["error"])

        return r

    def test_it_works(self):
        r = self.post(
            {
                "name": "Foo",
                "tags": "bar,baz",
                "desc": "description goes here",
                "timeout": 3600,
                "grace": 60,
                "start_kw": "START",
                "success_kw": "SUCCESS",
                "failure_kw": "FAILURE",
                "filter_subject": True,
                "filter_body": True,
            }
        )

        self.assertEqual(r.status_code, 201)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        assert "ping_url" in doc
        self.assertEqual(doc["name"], "Foo")
        self.assertEqual(doc["slug"], "foo")
        self.assertEqual(doc["tags"], "bar,baz")
        self.assertEqual(doc["desc"], "description goes here")
        self.assertEqual(doc["last_ping"], None)
        self.assertEqual(doc["n_pings"], 0)
        self.assertEqual(doc["methods"], "")
        self.assertEqual(doc["start_kw"], "START")
        self.assertEqual(doc["success_kw"], "SUCCESS")
        self.assertEqual(doc["failure_kw"], "FAILURE")
        self.assertTrue(doc["filter_subject"])
        self.assertTrue(doc["filter_body"])

        self.assertTrue("schedule" not in doc)
        self.assertTrue("tz" not in doc)

        check = Check.objects.get()
        self.assertEqual(check.name, "Foo")
        self.assertEqual(check.slug, "foo")
        self.assertEqual(check.tags, "bar,baz")
        self.assertEqual(check.desc, "description goes here")
        self.assertEqual(check.methods, "")
        self.assertEqual(check.start_kw, "START")
        self.assertEqual(check.success_kw, "SUCCESS")
        self.assertEqual(check.failure_kw, "FAILURE")
        self.assertTrue(check.filter_subject)
        self.assertTrue(check.filter_body)
        self.assertEqual(check.timeout.total_seconds(), 3600)
        self.assertEqual(check.grace.total_seconds(), 60)
        self.assertEqual(check.project, self.project)

    def test_it_handles_options(self):
        r = self.client.options(self.URL)
        self.assertEqual(r.status_code, 204)
        self.assertIn("POST", r["Access-Control-Allow-Methods"])

    def test_30_days_works(self):
        r = self.post({"name": "Foo", "timeout": 2592000, "grace": 2592000})

        self.assertEqual(r.status_code, 201)

        check = Check.objects.get()
        self.assertEqual(check.timeout.total_seconds(), 2592000)
        self.assertEqual(check.grace.total_seconds(), 2592000)

    def test_it_accepts_api_key_in_header(self):
        payload = {"name": "Foo"}
        r = self.client.post(
            self.URL, payload, content_type="application/json", HTTP_X_API_KEY="X" * 32
        )

        self.assertEqual(r.status_code, 201)

    def test_it_assigns_channels(self):
        channel = Channel.objects.create(project=self.project)

        r = self.post({"channels": "*"})

        self.assertEqual(r.status_code, 201)
        check = Check.objects.get()
        self.assertEqual(check.channel_set.get(), channel)

    def test_it_sets_channel_by_name(self):
        channel = Channel.objects.create(project=self.project, name="alerts")

        r = self.post({"channels": "alerts"})
        self.assertEqual(r.status_code, 201)

        check = Check.objects.get()
        assigned_channel = check.channel_set.get()
        self.assertEqual(assigned_channel, channel)

    def test_it_sets_channel_by_name_formatted_as_uuid(self):
        name = "102eaa82-a274-4b15-a499-c1bb6bbcd7b6"
        channel = Channel.objects.create(project=self.project, name=name)

        r = self.post({"channels": name})
        self.assertEqual(r.status_code, 201)

        check = Check.objects.get()
        assigned_channel = check.channel_set.get()
        self.assertEqual(assigned_channel, channel)

    def test_it_handles_channel_lookup_by_name_with_no_results(self):
        r = self.post({"channels": "abc"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid channel identifier: abc")

        # The check should not have been saved
        self.assertFalse(Check.objects.exists())

    def test_it_handles_channel_lookup_by_name_with_multiple_results(self):
        Channel.objects.create(project=self.project, name="foo")
        Channel.objects.create(project=self.project, name="foo")

        r = self.post({"channels": "foo"})

        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "non-unique channel identifier: foo")

        # The check should not have been saved
        self.assertFalse(Check.objects.exists())

    def test_it_rejects_multiple_empty_channel_names(self):
        Channel.objects.create(project=self.project, name="")

        r = self.post({"channels": ","})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "empty channel identifier")

        # The check should not have been saved
        self.assertFalse(Check.objects.exists())

    def test_it_supports_unique_name(self):
        check = Check.objects.create(project=self.project, name="Foo")

        r = self.post({"name": "Foo", "tags": "bar", "unique": ["name"]})

        # Expect 200 instead of 201
        self.assertEqual(r.status_code, 200)

        # And there should be only one check in the database:
        self.assertEqual(Check.objects.count(), 1)

        # The tags field should have a value now:
        check.refresh_from_db()
        self.assertEqual(check.tags, "bar")

    def test_it_supports_unique_slug(self):
        check = Check.objects.create(project=self.project, slug="foo")

        r = self.post({"slug": "foo", "tags": "bar", "unique": ["slug"]})

        # Expect 200 instead of 201
        self.assertEqual(r.status_code, 200)

        # And there should be only one check in the database:
        self.assertEqual(Check.objects.count(), 1)

        # The tags field should have a value now:
        check.refresh_from_db()
        self.assertEqual(check.tags, "bar")

    def test_it_supports_unique_tags(self):
        Check.objects.create(project=self.project, tags="foo")

        r = self.post({"tags": "foo", "unique": ["tags"]})

        # Expect 200 instead of 201
        self.assertEqual(r.status_code, 200)

        # And there should be only one check in the database:
        self.assertEqual(Check.objects.count(), 1)

    def test_it_supports_unique_timeout(self):
        Check.objects.create(project=self.project, timeout=td(seconds=123))

        r = self.post({"timeout": 123, "unique": ["timeout"]})

        # Expect 200 instead of 201
        self.assertEqual(r.status_code, 200)

        # And there should be only one check in the database:
        self.assertEqual(Check.objects.count(), 1)

    def test_it_supports_unique_grace(self):
        Check.objects.create(project=self.project, grace=td(seconds=123))

        r = self.post({"grace": 123, "unique": ["grace"]})

        # Expect 200 instead of 201
        self.assertEqual(r.status_code, 200)

        # And there should be only one check in the database:
        self.assertEqual(Check.objects.count(), 1)

    def test_it_handles_empty_unique_parameter(self):
        check = Check.objects.create(project=self.project)

        r = self.post({"name": "Hello", "unique": []})

        # Expect 201
        self.assertEqual(r.status_code, 201)

        # The pre-existing check should be unchanged:
        check.refresh_from_db()
        self.assertEqual(check.name, "")

    def test_it_handles_missing_request_body(self):
        r = self.client.post(self.URL, content_type="application/json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["error"], "missing api key")

    def test_it_handles_invalid_json(self):
        r = self.client.post(
            self.URL, "this is not json", content_type="application/json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "could not parse request body")

    def test_it_rejects_wrong_api_key(self):
        r = self.post({"api_key": "Y" * 32})
        self.assertEqual(r.status_code, 401)

    def test_it_rejects_small_timeout(self):
        self.post({"timeout": 0}, expect_fragment="timeout is too small")

    def test_it_rejects_large_timeout(self):
        self.post({"timeout": 31536001}, expect_fragment="timeout is too large")

    def test_it_rejects_non_number_timeout(self):
        self.post({"timeout": "oops"}, expect_fragment="timeout is not a number")

    def test_it_rejects_non_string_name(self):
        self.post({"name": False}, expect_fragment="name is not a string")

    def test_it_rejects_long_name(self):
        self.post({"name": "01234567890" * 20}, expect_fragment="name is too long")

    def test_unique_accepts_only_specific_values(self):
        self.post(
            {"name": "Foo", "unique": ["status"]},
            expect_fragment="unexpected value",
        )

    def test_it_rejects_bad_unique_values(self):
        self.post(
            {"name": "Foo", "unique": "not a list"},
            expect_fragment="not an array",
        )

    def test_it_supports_cron_syntax(self):
        r = self.post({"schedule": "5 * * * *", "tz": "Europe/Riga", "grace": 60})

        self.assertEqual(r.status_code, 201)

        doc = r.json()
        self.assertEqual(doc["schedule"], "5 * * * *")
        self.assertEqual(doc["tz"], "Europe/Riga")
        self.assertEqual(doc["grace"], 60)

        self.assertTrue("timeout" not in doc)

    def test_it_validates_cron_expression(self):
        r = self.post({"schedule": "bad-expression", "tz": "Europe/Riga", "grace": 60})
        self.assertEqual(r.status_code, 400)

    def test_it_validates_timezone(self):
        r = self.post({"schedule": "* * * * *", "tz": "not-a-timezone", "grace": 60})
        self.assertEqual(r.status_code, 400)

    def test_it_sets_default_timeout(self):
        r = self.post({})
        self.assertEqual(r.status_code, 201)

        doc = r.json()
        self.assertEqual(doc["timeout"], 86400)

    def test_it_obeys_check_limit(self):
        self.profile.check_limit = 0
        self.profile.save()

        r = self.post({})
        self.assertEqual(r.status_code, 403)

    def test_it_rejects_readonly_key(self):
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.post({"api_key": "R" * 32, "name": "Foo"})
        self.assertEqual(r.status_code, 401)

    def test_it_sets_manual_resume(self):
        r = self.post({"manual_resume": True})

        self.assertEqual(r.status_code, 201)
        check = Check.objects.get()
        self.assertTrue(check.manual_resume)

    def test_it_rejects_non_boolean_manual_resume(self):
        r = self.post({"manual_resume": "surprise"})

        self.assertEqual(r.status_code, 400)

    def test_it_sets_methods(self):
        r = self.post({"methods": "POST"})

        self.assertEqual(r.status_code, 201)
        check = Check.objects.get()
        self.assertEqual(check.methods, "POST")

    def test_it_rejects_bad_methods_value(self):
        r = self.post({"methods": "bad-value"})
        self.assertEqual(r.status_code, 400)

    def test_it_sets_success_kw(self):
        r = self.post({"subject": "SUCCESS,COMPLETE"})
        self.assertEqual(r.status_code, 201)
        check = Check.objects.get()
        self.assertTrue(check.filter_subject)
        self.assertEqual(check.success_kw, "SUCCESS,COMPLETE")

    def test_it_sets_failure_kw(self):
        r = self.post({"subject_fail": "FAILED,FAILURE"})
        self.assertEqual(r.status_code, 201)
        check = Check.objects.get()
        self.assertTrue(check.filter_subject)
        self.assertEqual(check.failure_kw, "FAILED,FAILURE")

    def test_it_rejects_non_string_subject(self):
        self.post({"subject": False}, expect_fragment="subject is not a string")

    def test_it_rejects_non_string_subject_fail(self):
        msg = "subject_fail is not a string"
        self.post({"subject_fail": False}, expect_fragment=msg)

    def test_v2_reports_started_separately(self):
        Check.objects.create(project=self.project, name="X", last_start=now())

        r = self.post({"name": "X", "unique": ["name"]}, v=2)
        # Expect 200 instead of 201
        self.assertEqual(r.status_code, 200)

        doc = r.json()
        self.assertEqual(doc["status"], "new")
        self.assertTrue(doc["started"])

    def test_v3_saves_slug(self):
        r = self.post({"name": "Foo", "slug": "custom-slug"}, v=3)
        self.assertEqual(r.status_code, 201)

        check = Check.objects.get()
        self.assertEqual(check.name, "Foo")
        self.assertEqual(check.slug, "custom-slug")

    def test_v3_does_not_autogenerate_slug(self):
        r = self.post({"name": "Foo"}, v=3)
        self.assertEqual(r.status_code, 201)

        check = Check.objects.get()
        self.assertEqual(check.slug, "")

    def test_it_handles_invalid_slug(self):
        for slug in ["Uppercase", "special!", "look spaces"]:
            r = self.post({"name": "Foo", "slug": "Hey!"}, v=3)
            self.assertEqual(r.status_code, 400)
            self.assertEqual(
                r.json()["error"], "json validation error: slug does not match pattern"
            )
