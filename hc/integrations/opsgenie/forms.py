from __future__ import annotations

from django import forms


class AddOpsgenieForm(forms.Form):
    error_css_class = "has-error"
    region = forms.ChoiceField(initial="us", choices=(("us", "US"), ("eu", "EU")))
    key = forms.CharField(max_length=40)
