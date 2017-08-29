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

    value_down = forms.URLField(max_length=1000, required=False,
                                validators=[WebhookValidator()])

    value_up = forms.URLField(max_length=1000, required=False,
                              validators=[WebhookValidator()])

    post_data = forms.CharField(max_length=1000, required=False)

    def get_value(self):
        d = self.cleaned_data
        return "\n".join((d["value_down"], d["value_up"], d["post_data"]))


phone_validator = RegexValidator(regex='^\+\d{5,15}$',
                                 message="Invalid phone number format.")


class AddSmsForm(forms.Form):
    error_css_class = "has-error"
    value = forms.CharField(max_length=16, validators=[phone_validator])
