from __future__ import annotations

import json
import re
from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from typing import Any

from django import forms
from django.core.exceptions import ValidationError

from hc.front.validators import (
    CronValidator,
    OnCalendarValidator,
    TimezoneValidator,
    WebhookValidator,
)
from hc.lib import matrix


def _is_latin1(s: str) -> bool:
    try:
        s.encode("latin-1")
        return True
    except UnicodeError:
        return False


class LaxURLField(forms.URLField):
    default_validators = [WebhookValidator()]


class HeadersField(forms.Field):
    message = """Use "Header-Name: value" pairs, one per line."""

    def to_python(self, value: str | None) -> dict[str, str]:
        if not value:
            return {}

        headers = {}
        for line in value.split("\n"):
            if not line.strip():
                continue

            if ":" not in line:
                raise ValidationError(self.message)

            n, v = line.split(":", maxsplit=1)
            n, v = n.strip(), v.strip()
            if not n or not v:
                raise ValidationError(message=self.message)

            if not _is_latin1(n):
                raise ValidationError(
                    message="Header names must not contain special characters"
                )

            headers[n] = v

        return headers

    def validate(self, value: dict[str, str]) -> None:
        super().validate(value)
        for k, v in value.items():
            if len(k) > 1000 or len(v) > 1000:
                raise ValidationError("Value too long")


class NameTagsForm(forms.Form):
    name = forms.CharField(max_length=100, required=False)
    slug = forms.SlugField(max_length=100, required=False)
    tags = forms.CharField(max_length=500, required=False)
    desc = forms.CharField(required=False)

    def clean_tags(self) -> str:
        result = []

        for part in self.cleaned_data["tags"].split(" "):
            part = part.strip()
            if part != "":
                result.append(part)

        return " ".join(result)


class AddCheckForm(NameTagsForm):
    kind = forms.ChoiceField(
        choices=(("simple", "simple"), ("cron", "cron"), ("oncalendar", "oncalendar"))
    )
    timeout = forms.IntegerField(min_value=60, max_value=31536000)
    schedule = forms.CharField(required=False, max_length=100)
    tz = forms.CharField(max_length=36, validators=[TimezoneValidator()])
    grace = forms.IntegerField(min_value=60, max_value=31536000)

    def clean_timeout(self) -> td:
        return td(seconds=self.cleaned_data["timeout"])

    def clean_grace(self) -> td:
        return td(seconds=self.cleaned_data["grace"])

    def clean_schedule(self):
        kind = self.cleaned_data.get("kind")
        validator = None
        if kind == "cron":
            validator = CronValidator()
        elif kind == "oncalendar":
            validator = OnCalendarValidator()
        else:
            # If kind is not cron or oncalendar, ignore the passed in value
            # and use "* * * * *" instead.
            return "* * * * *"

        validator(self.cleaned_data["schedule"])
        return self.cleaned_data["schedule"]


class FilteringRulesForm(forms.Form):
    filter_subject = forms.BooleanField(required=False)
    filter_body = forms.BooleanField(required=False)
    start_kw = forms.CharField(required=False, max_length=200)
    success_kw = forms.CharField(required=False, max_length=200)
    failure_kw = forms.CharField(required=False, max_length=200)
    methods = forms.ChoiceField(required=False, choices=(("", "Any"), ("POST", "POST")))
    manual_resume = forms.BooleanField(required=False)


class TimeoutForm(forms.Form):
    timeout = forms.IntegerField(min_value=60, max_value=31536000)
    grace = forms.IntegerField(min_value=60, max_value=31536000)

    def clean_timeout(self) -> td:
        return td(seconds=self.cleaned_data["timeout"])

    def clean_grace(self) -> td:
        return td(seconds=self.cleaned_data["grace"])


class CronForm(forms.Form):
    schedule = forms.CharField(max_length=100, validators=[CronValidator()])
    tz = forms.CharField(max_length=36, validators=[TimezoneValidator()])
    grace = forms.IntegerField(min_value=1, max_value=43200)


class OnCalendarForm(forms.Form):
    schedule = forms.CharField(max_length=100, validators=[OnCalendarValidator()])
    tz = forms.CharField(max_length=36, validators=[TimezoneValidator()])
    grace = forms.IntegerField(min_value=1, max_value=43200)


class AddOpsgenieForm(forms.Form):
    error_css_class = "has-error"
    region = forms.ChoiceField(initial="us", choices=(("us", "US"), ("eu", "EU")))
    key = forms.CharField(max_length=40)


class AddPushoverForm(forms.Form):
    error_css_class = "has-error"
    pushover_user_key = forms.CharField()
    prio = forms.IntegerField(initial=0, min_value=-3, max_value=2)
    prio_up = forms.IntegerField(initial=0, min_value=-3, max_value=2)

    def get_value(self) -> str:
        key = self.cleaned_data["pushover_user_key"]
        prio = self.cleaned_data["prio"]
        prio_up = self.cleaned_data["prio_up"]
        return "%s|%s|%s" % (key, prio, prio_up)


class EmailForm(forms.Form):
    error_css_class = "has-error"
    value = forms.EmailField(max_length=100)
    down = forms.BooleanField(required=False, initial=True)
    up = forms.BooleanField(required=False, initial=True)

    def clean(self) -> None:
        super().clean()

        down = self.cleaned_data.get("down")
        up = self.cleaned_data.get("up")

        if not down and not up:
            self.add_error("down", "Please select at least one.")

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)


class AddUrlForm(forms.Form):
    error_css_class = "has-error"
    value = LaxURLField(max_length=1000)


METHODS = ("GET", "POST", "PUT")


class WebhookForm(forms.Form):
    error_css_class = "has-error"
    name = forms.CharField(max_length=100, required=False)

    method_down = forms.ChoiceField(initial="GET", choices=zip(METHODS, METHODS))
    body_down = forms.CharField(max_length=1000, required=False)
    headers_down = HeadersField(required=False)
    url_down = LaxURLField(max_length=1000, required=False)

    method_up = forms.ChoiceField(initial="GET", choices=zip(METHODS, METHODS))
    body_up = forms.CharField(max_length=1000, required=False)
    headers_up = HeadersField(required=False)
    url_up = LaxURLField(max_length=1000, required=False)

    def clean(self) -> None:
        super().clean()

        url_down = self.cleaned_data.get("url_down")
        url_up = self.cleaned_data.get("url_up")

        if not url_down and not url_up:
            if not self.has_error("url_down"):
                self.add_error("url_down", "Enter a valid URL.")

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)


class AddShellForm(forms.Form):
    error_css_class = "has-error"

    cmd_down = forms.CharField(max_length=1000, required=False)
    cmd_up = forms.CharField(max_length=1000, required=False)

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)


class PhoneNumberForm(forms.Form):
    error_css_class = "has-error"
    label = forms.CharField(max_length=100, required=False)
    phone = forms.CharField()

    def clean_phone(self) -> str:
        v = self.cleaned_data["phone"]

        stripped = v.encode("ascii", "ignore").decode("ascii")
        assert isinstance(stripped, str)
        stripped = stripped.replace(" ", "").replace("-", "")
        if not re.match(r"^\+\d{5,15}$", stripped):
            raise forms.ValidationError("Invalid phone number format.")

        return stripped

    def get_json(self) -> str:
        return json.dumps({"value": self.cleaned_data["phone"]})


class PhoneUpDownForm(PhoneNumberForm):
    up = forms.BooleanField(required=False, initial=True)
    down = forms.BooleanField(required=False, initial=True)

    def clean(self) -> None:
        super().clean()

        down = self.cleaned_data.get("down")
        up = self.cleaned_data.get("up")

        if not down and not up:
            self.add_error("down", "Please select at least one.")

    def get_json(self) -> str:
        return json.dumps(
            {
                "value": self.cleaned_data["phone"],
                "up": self.cleaned_data["up"],
                "down": self.cleaned_data["down"],
            }
        )


class ChannelNameForm(forms.Form):
    name = forms.CharField(max_length=100, required=False)


class AddMatrixForm(forms.Form):
    error_css_class = "has-error"
    alias = forms.CharField(max_length=100)

    def clean_alias(self) -> str:
        v = self.cleaned_data["alias"]
        assert isinstance(v, str)

        # validate it by trying to join
        try:
            self.cleaned_data["room_id"] = matrix.join(v)
        except matrix.JoinError as e:
            raise forms.ValidationError(e.message)

        return v


class AddAppriseForm(forms.Form):
    error_css_class = "has-error"
    url = forms.CharField(max_length=512)


class AddPdForm(forms.Form):
    error_css_class = "has-error"
    value = forms.CharField(max_length=32)


ZULIP_TARGETS = (("stream", "Stream"), ("private", "Private"))


class AddZulipForm(forms.Form):
    error_css_class = "has-error"
    bot_email = forms.EmailField(max_length=100)
    api_key = forms.CharField(max_length=50)
    site = LaxURLField(max_length=100)
    mtype = forms.ChoiceField(choices=ZULIP_TARGETS)
    to = forms.CharField(max_length=100)
    topic = forms.CharField(max_length=100, required=False)

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)


class AddTrelloForm(forms.Form):
    token = forms.RegexField(regex=r"^[0-9a-fA-F]{64,256}$")
    board_name = forms.CharField(max_length=100)
    list_name = forms.CharField(max_length=100)
    list_id = forms.RegexField(regex=r"^[0-9a-fA-F]{16,32}$")

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)


class AddGotifyForm(forms.Form):
    error_css_class = "has-error"
    token = forms.CharField(max_length=50)
    url = LaxURLField(max_length=1000)

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)


class GroupForm(forms.Form):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        project = kwargs.pop("project")
        super().__init__(*args, **kwargs)

        assert isinstance(self.fields["channels"], forms.MultipleChoiceField)
        self.fields["channels"].choices = (
            (c.code, c) for c in project.channel_set.exclude(kind="group")
        )

    error_css_class = "has-error"
    label = forms.CharField(max_length=100, required=False)
    channels = forms.MultipleChoiceField()

    def get_value(self) -> str:
        return ",".join(self.cleaned_data["channels"])


class NtfyForm(forms.Form):
    error_css_class = "has-error"
    topic = forms.CharField(max_length=50)
    url = LaxURLField(max_length=1000)
    token = forms.CharField(max_length=100, required=False)
    priority = forms.IntegerField(initial=3, min_value=0, max_value=5)
    priority_up = forms.IntegerField(initial=3, min_value=0, max_value=5)

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)


class SearchForm(forms.Form):
    q = forms.RegexField(regex=r"^[0-9a-zA-Z\s]{3,100}$")


class SeekForm(forms.Form):
    # min_value is 2010-01-01, max_value is 2030-01-01
    start = forms.IntegerField(min_value=1262296800, max_value=1893448800)
    end = forms.IntegerField(min_value=1262296800, max_value=1893448800)

    def clean_start(self) -> datetime:
        return datetime.fromtimestamp(self.cleaned_data["start"], tz=timezone.utc)

    def clean_end(self) -> datetime:
        return datetime.fromtimestamp(self.cleaned_data["end"], tz=timezone.utc)


class TransferForm(forms.Form):
    project = forms.UUIDField()


class AddTelegramForm(forms.Form):
    project = forms.UUIDField()
