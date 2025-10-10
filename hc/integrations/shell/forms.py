from __future__ import annotations

import json

from django import forms


class AddShellForm(forms.Form):
    error_css_class = "has-error"

    cmd_down = forms.CharField(max_length=1000, required=False)
    cmd_up = forms.CharField(max_length=1000, required=False)

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
