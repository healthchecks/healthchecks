from __future__ import annotations

import json

from django import forms

from hc.front.forms import LaxURLField


class AddGotifyForm(forms.Form):
    error_css_class = "has-error"
    PRIORITY_CHOICES = [
        (0, "Disabled: Does not notify about Down events"),
        (2, "Low Priority: Quiet icon in notification bar."),
        (5, "Normal Priority: Sends a notification with sound."),
        (9, "High Priority: Sends a notification with sound and vibration."),
    ]

    token = forms.CharField(max_length=50)
    url = LaxURLField(max_length=1000, assume_scheme="https")
    priority = forms.TypedChoiceField(choices=PRIORITY_CHOICES, coerce=int, initial=5)
    priority_up = forms.TypedChoiceField(
        choices=PRIORITY_CHOICES, coerce=int, initial=5
    )

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
