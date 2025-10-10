from __future__ import annotations

import json

from django import forms


class AddTrelloForm(forms.Form):
    token = forms.CharField(max_length=1000)
    board_name = forms.CharField(max_length=100)
    list_name = forms.CharField(max_length=100)
    list_id = forms.RegexField(regex=r"^[0-9a-fA-F]{16,32}$")

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
