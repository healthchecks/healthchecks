from __future__ import annotations

import json

from django import forms
from hc.front.forms import LaxURLField


class AddGotifyForm(forms.Form):
    error_css_class = "has-error"
    token = forms.CharField(max_length=50)
    url = LaxURLField(max_length=1000, assume_scheme="https")

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
