from __future__ import annotations

import json

from django import forms
from hc.front.forms import LaxURLField

ZULIP_TARGETS = (("stream", "Stream"), ("private", "Private"))


class AddZulipForm(forms.Form):
    error_css_class = "has-error"
    bot_email = forms.EmailField(max_length=100)
    api_key = forms.CharField(max_length=50)
    site = LaxURLField(max_length=100, assume_scheme="https")
    mtype = forms.ChoiceField(choices=ZULIP_TARGETS)
    to = forms.CharField(max_length=100)
    topic = forms.CharField(max_length=100, required=False)

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
