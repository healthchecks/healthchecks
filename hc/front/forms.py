from django import forms

from hc.api.models import TIMEOUT_CHOICES


class TimeoutForm(forms.Form):
    timeout = forms.ChoiceField(choices=TIMEOUT_CHOICES)
