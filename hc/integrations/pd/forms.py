from __future__ import annotations

from django import forms


class AddPdForm(forms.Form):
    error_css_class = "has-error"
    value = forms.CharField(max_length=32)
