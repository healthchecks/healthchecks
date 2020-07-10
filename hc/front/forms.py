from datetime import timedelta as td
import json
from urllib.parse import quote, urlencode

from django import forms
from django.forms import URLField
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from hc.front.validators import (
    CronExpressionValidator,
    TimezoneValidator,
    WebhookValidator,
)
import requests


class HeadersField(forms.Field):
    message = """Use "Header-Name: value" pairs, one per line."""

    def to_python(self, value):
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

            headers[n] = v

        return headers

    def validate(self, value):
        super().validate(value)
        for k, v in value.items():
            if len(k) > 1000 or len(v) > 1000:
                raise ValidationError("Value too long")


class NameTagsForm(forms.Form):
    name = forms.CharField(max_length=100, required=False)
    tags = forms.CharField(max_length=500, required=False)
    desc = forms.CharField(required=False)

    def clean_tags(self):
        result = []

        for part in self.cleaned_data["tags"].split(" "):
            part = part.strip()
            if part != "":
                result.append(part)

        return " ".join(result)


class FilteringRulesForm(forms.Form):
    subject = forms.CharField(required=False, max_length=100)
    methods = forms.ChoiceField(required=False, choices=(("", "Any"), ("POST", "POST")))
    manual_resume = forms.BooleanField(required=False)


class TimeoutForm(forms.Form):
    timeout = forms.IntegerField(min_value=60, max_value=2592000)
    grace = forms.IntegerField(min_value=60, max_value=2592000)

    def clean_timeout(self):
        return td(seconds=self.cleaned_data["timeout"])

    def clean_grace(self):
        return td(seconds=self.cleaned_data["grace"])


class CronForm(forms.Form):
    schedule = forms.CharField(max_length=100, validators=[CronExpressionValidator()])
    tz = forms.CharField(max_length=36, validators=[TimezoneValidator()])
    grace = forms.IntegerField(min_value=1, max_value=43200)


class AddOpsGenieForm(forms.Form):
    error_css_class = "has-error"
    region = forms.ChoiceField(initial="us", choices=(("us", "US"), ("eu", "EU")))
    key = forms.CharField(max_length=40)


PRIO_CHOICES = [
    ("-2", "Lowest Priority"),
    ("-1", "Low Priority"),
    ("0", "Normal Priority"),
    ("1", "High Priority"),
    ("2", "Emergency Priority"),
]


class AddPushoverForm(forms.Form):
    error_css_class = "has-error"
    pushover_user_key = forms.CharField()
    prio = forms.ChoiceField(initial="0", choices=PRIO_CHOICES)
    prio_up = forms.ChoiceField(initial="0", choices=PRIO_CHOICES)

    def get_value(self):
        key = self.cleaned_data["pushover_user_key"]
        prio = self.cleaned_data["prio"]
        prio_up = self.cleaned_data["prio_up"]
        return "%s|%s|%s" % (key, prio, prio_up)


class AddEmailForm(forms.Form):
    error_css_class = "has-error"
    value = forms.EmailField(max_length=100)
    down = forms.BooleanField(required=False, initial=True)
    up = forms.BooleanField(required=False, initial=True)

    def clean(self):
        super().clean()

        down = self.cleaned_data.get("down")
        up = self.cleaned_data.get("up")

        if not down and not up:
            self.add_error("down", "Please select at least one.")


class AddUrlForm(forms.Form):
    error_css_class = "has-error"
    value = forms.URLField(max_length=1000, validators=[WebhookValidator()])


METHODS = ("GET", "POST", "PUT")


class WebhookForm(forms.Form):
    error_css_class = "has-error"
    name = forms.CharField(max_length=100, required=False)

    method_down = forms.ChoiceField(initial="GET", choices=zip(METHODS, METHODS))
    body_down = forms.CharField(max_length=1000, required=False)
    headers_down = HeadersField(required=False)
    url_down = URLField(
        max_length=1000, required=False, validators=[WebhookValidator()]
    )

    method_up = forms.ChoiceField(initial="GET", choices=zip(METHODS, METHODS))
    body_up = forms.CharField(max_length=1000, required=False)
    headers_up = HeadersField(required=False)
    url_up = forms.URLField(
        max_length=1000, required=False, validators=[WebhookValidator()]
    )

    def clean(self):
        super().clean()

        url_down = self.cleaned_data.get("url_down")
        url_up = self.cleaned_data.get("url_up")

        if not url_down and not url_up:
            if not self.has_error("url_down"):
                self.add_error("url_down", "Enter a valid URL.")

    def get_value(self):
        return json.dumps(dict(self.cleaned_data), sort_keys=True)


class AddShellForm(forms.Form):
    error_css_class = "has-error"

    cmd_down = forms.CharField(max_length=1000, required=False)
    cmd_up = forms.CharField(max_length=1000, required=False)

    def get_value(self):
        return json.dumps(dict(self.cleaned_data), sort_keys=True)


phone_validator = RegexValidator(
    regex="^\+\d{5,15}$", message="Invalid phone number format."
)


class AddSmsForm(forms.Form):
    error_css_class = "has-error"
    label = forms.CharField(max_length=100, required=False)
    value = forms.CharField(max_length=16, validators=[phone_validator])
    down = forms.BooleanField(required=False, initial=True)
    up = forms.BooleanField(required=False, initial=True)


class ChannelNameForm(forms.Form):
    name = forms.CharField(max_length=100, required=False)


class AddMatrixForm(forms.Form):
    error_css_class = "has-error"
    alias = forms.CharField(max_length=100)

    def clean_alias(self):
        v = self.cleaned_data["alias"]

        # validate it by trying to join
        url = settings.MATRIX_HOMESERVER
        url += "/_matrix/client/r0/join/%s?" % quote(v)
        url += urlencode({"access_token": settings.MATRIX_ACCESS_TOKEN})
        r = requests.post(url, {})
        if r.status_code == 429:
            raise forms.ValidationError(
                "Matrix server returned status code 429 (Too Many Requests), "
                "please try again later."
            )

        doc = r.json()
        if "error" in doc:
            raise forms.ValidationError("Response from Matrix: %s" % doc["error"])

        self.cleaned_data["room_id"] = doc["room_id"]

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
    mtype = forms.ChoiceField(choices=ZULIP_TARGETS)
    to = forms.CharField(max_length=100)

    def get_value(self):
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
