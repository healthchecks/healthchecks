from __future__ import annotations

import json

from django import forms
from hc.front.forms import LaxURLField


class NtfyForm(forms.Form):
    error_css_class = "has-error"
    topic = forms.CharField(max_length=64)
    url = LaxURLField(max_length=1000, assume_scheme="https")
    token = forms.CharField(max_length=100, required=False)
    priority = forms.IntegerField(initial=3, min_value=0, max_value=5)
    priority_up = forms.IntegerField(initial=3, min_value=0, max_value=5)

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
