from __future__ import annotations

import json

from django import forms

from hc.front.forms import LaxURLField


class NtfyForm(forms.Form):
    error_css_class = "has-error"
    PRIORITY_CHOICES = [
        (
            5,
            "Max priority: Really long vibration bursts,"
            " default notification sound with a pop-over notification.",
        ),
        (
            4,
            "High priority: Long vibration burst,"
            " default notification sound with a pop-over notification.",
        ),
        (
            3,
            "Default priority: Short default vibration and sound."
            " Default notification behavior.",
        ),
        (
            2,
            "Low priority: No vibration or sound."
            " Notification will not visibly show up until"
            " notification drawer is pulled down.",
        ),
        (
            1,
            "Min priority: No vibration or sound."
            " The notification will be under the fold in 'Other notifications'.",
        ),
        (0, "Disabled: Will not notify."),
    ]

    topic = forms.CharField(max_length=64)
    url = LaxURLField(max_length=1000, assume_scheme="https")
    token = forms.CharField(max_length=100, required=False)

    priority = forms.TypedChoiceField(choices=PRIORITY_CHOICES, coerce=int, initial=3)
    priority_up = forms.TypedChoiceField(
        choices=PRIORITY_CHOICES, coerce=int, initial=3
    )

    # Add "no-caret" CSS class to the <select> elements
    priority.widget.attrs["class"] = "no-caret"
    priority_up.widget.attrs["class"] = "no-caret"

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
