from django import forms
from hc.api.models import Channel


class TimeoutForm(forms.Form):
    timeout = forms.IntegerField(min_value=60, max_value=604800)
    grace = forms.IntegerField(min_value=60, max_value=604800)


class AddChannelForm(forms.ModelForm):

    class Meta:
        model = Channel
        fields = ['kind', 'value']
