from datetime import timedelta as td
import json
import re
from urllib.parse import quote, urlencode

from django import forms
from django.conf import settings
from django.core.validators import RegexValidator
from hc.front.validators import (CronExpressionValidator, TimezoneValidator,
                                 WebhookValidator)
import requests


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


class EmailSettingsForm(forms.Form):
    subject = forms.CharField(max_length=100)


class TimeoutForm(forms.Form):
    timeout = forms.IntegerField(min_value=60, max_value=2592000)
    grace = forms.IntegerField(min_value=60, max_value=2592000)

    def clean_timeout(self):
        return td(seconds=self.cleaned_data["timeout"])

    def clean_grace(self):
        return td(seconds=self.cleaned_data["grace"])


class CronForm(forms.Form):
    schedule = forms.CharField(max_length=100,
                               validators=[CronExpressionValidator()])
    tz = forms.CharField(max_length=36, validators=[TimezoneValidator()])
    grace = forms.IntegerField(min_value=1, max_value=43200)


class AddOpsGenieForm(forms.Form):
    error_css_class = "has-error"
    value = forms.CharField(max_length=40)


class AddEmailForm(forms.Form):
    error_css_class = "has-error"
    value = forms.EmailField(max_length=100)


class AddUrlForm(forms.Form):
    error_css_class = "has-error"
    value = forms.URLField(max_length=1000, validators=[WebhookValidator()])


_valid_header_name = re.compile(r'\A[^:\s][^:\r\n]*\Z').match


class AddWebhookForm(forms.Form):
    error_css_class = "has-error"

    url_down = forms.URLField(max_length=1000, required=False,
                              validators=[WebhookValidator()])

    url_up = forms.URLField(max_length=1000, required=False,
                            validators=[WebhookValidator()])

    post_data = forms.CharField(max_length=1000, required=False)

    def __init__(self, *args, **kwargs):
        super(AddWebhookForm, self).__init__(*args, **kwargs)

        self.invalid_header_names = set()
        self.headers = {}
        if "header_key[]" in self.data and "header_value[]" in self.data:
            keys = self.data.getlist("header_key[]")
            values = self.data.getlist("header_value[]")
            for key, value in zip(keys, values):
                if not key:
                    continue

                if not _valid_header_name(key):
                    self.invalid_header_names.add(key)

                self.headers[key] = value

    def clean(self):
        if self.invalid_header_names:
            raise forms.ValidationError("Invalid header names")

        return self.cleaned_data

    def get_value(self):
        val = dict(self.cleaned_data)
        val["headers"] = self.headers
        return json.dumps(val, sort_keys=True)


phone_validator = RegexValidator(regex='^\+\d{5,15}$',
                                 message="Invalid phone number format.")


class AddSmsForm(forms.Form):
    error_css_class = "has-error"
    label = forms.CharField(max_length=100, required=False)
    value = forms.CharField(max_length=16, validators=[phone_validator])


class ChannelNameForm(forms.Form):
    name = forms.CharField(max_length=100, required=False)


class AddMatrixForm(forms.Form):
    error_css_class = "has-error"
    alias = forms.CharField(max_length=40)

    def clean_alias(self):
        v = self.cleaned_data["alias"]

        # validate it by trying to join
        url = settings.MATRIX_HOMESERVER
        url += "/_matrix/client/r0/join/%s?" % quote(v)
        url += urlencode({"access_token": settings.MATRIX_ACCESS_TOKEN})
        doc = requests.post(url, {}).json()
        if "error" in doc:
            raise forms.ValidationError(
                "Response from Matrix: %s" % doc["error"])

        self.cleaned_data["room_id"] = doc["room_id"]

        return v
