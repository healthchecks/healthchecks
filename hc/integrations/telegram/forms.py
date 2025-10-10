from __future__ import annotations


from django import forms


class AddTelegramForm(forms.Form):
    project = forms.UUIDField()
