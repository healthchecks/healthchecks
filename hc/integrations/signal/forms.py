from __future__ import annotations

import json
import re

from django import forms


class SignalRecipientForm(forms.Form):
    error_css_class = "has-error"
    label = forms.CharField(max_length=100, required=False)
    recipient = forms.CharField()

    def clean_recipient(self) -> str:
        v = self.cleaned_data["recipient"]
        assert isinstance(v, str)

        stripped = v.encode("ascii", "ignore").decode("ascii")
        stripped = stripped.replace(" ", "").replace("-", "")
        if "." in stripped:
            # Assume it is a username
            if not re.match(r"^\w{3,48}\.\d{2,10}$", stripped):
                raise forms.ValidationError("Invalid username format.")
        else:
            # Assume it is a phone number
            if not re.match(r"^\+\d{5,15}$", stripped):
                raise forms.ValidationError("Invalid phone number format.")

        return stripped


class SignalForm(SignalRecipientForm):
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
                "value": self.cleaned_data["recipient"],
                "up": self.cleaned_data["up"],
                "down": self.cleaned_data["down"],
            }
        )
