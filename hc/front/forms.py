import json
from datetime import timedelta as td

from django import forms
from django.core.validators import RegexValidator
from hc.front.validators import (CronExpressionValidator, TimezoneValidator,
                                 WebhookValidator)


class NameTagsForm(forms.Form):
    name = forms.CharField(max_length=100, required=False)
    tags = forms.CharField(max_length=500, required=False)

    def clean_tags(self):
        result = []

        for part in self.cleaned_data["tags"].split(" "):
            part = part.strip()
            if part != "":
                result.append(part)

        return " ".join(result)


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


class AddWebhookForm(forms.Form):
    error_css_class = "has-error"

    url_down = forms.URLField(max_length=1000, required=False,
                                validators=[WebhookValidator()])

    url_up = forms.URLField(max_length=1000, required=False,
                              validators=[WebhookValidator()])

    post_data = forms.CharField(max_length=1000, required=False)

    def __init__(self, *args, **kwargs):
        self.headers = {}
        if all(k in kwargs for k in ("header_keys", "header_values")):
            header_keys = kwargs.pop("header_keys")
            header_values = kwargs.pop("header_values")

            for i, (key, val) in enumerate(zip(header_keys, header_values)):
                if key:
                    self.headers[key] = val

        super(AddWebhookForm, self).__init__(*args, **kwargs)

    def get_value(self):
        val = dict(self.cleaned_data)
        val["headers"] = self.headers
        return json.dumps(val, sort_keys=True)


phone_validator = RegexValidator(regex='^\+\d{5,15}$',
                                 message="Invalid phone number format.")


class AddSmsForm(forms.Form):
    error_css_class = "has-error"
    value = forms.CharField(max_length=16, validators=[phone_validator])
