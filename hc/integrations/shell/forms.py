from __future__ import annotations

import json

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError


class AddShellForm(forms.Form):
    error_css_class = "has-error"

    cmd_down = forms.CharField(max_length=1000, required=False)
    cmd_up = forms.CharField(max_length=1000, required=False)

    def clean(self):
        super().clean()
        if not getattr(settings, "SHELL_ENABLED", False):
            raise ValidationError(
                "Shell commands are disabled. To enable them, set "
                "SHELL_ENABLED=True in local_settings.py."
            )

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
