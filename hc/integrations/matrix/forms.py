from __future__ import annotations

from django import forms
from hc.integrations.matrix import client


class AddMatrixForm(forms.Form):
    error_css_class = "has-error"
    alias = forms.CharField(max_length=100)

    def clean_alias(self) -> str:
        v = self.cleaned_data["alias"]
        assert isinstance(v, str)

        # validate it by trying to join
        try:
            self.cleaned_data["room_id"] = client.join(v)
        except client.JoinError as e:
            raise forms.ValidationError(e.message)

        return v
