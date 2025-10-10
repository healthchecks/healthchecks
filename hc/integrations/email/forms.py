from __future__ import annotations

import json

from django import forms


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
