from django import forms


class TimeoutForm(forms.Form):
    timeout = forms.IntegerField(min_value=60, max_value=604800)
    grace = forms.IntegerField(min_value=60, max_value=604800)
