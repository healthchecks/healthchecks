from __future__ import annotations


from django import forms


class AddAppriseForm(forms.Form):
    error_css_class = "has-error"
    url = forms.CharField(max_length=512)
