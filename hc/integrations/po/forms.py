from __future__ import annotations


from django import forms


class AddPushoverForm(forms.Form):
    error_css_class = "has-error"
    pushover_user_key = forms.CharField()
    prio = forms.IntegerField(initial=0, min_value=-3, max_value=2)
    prio_up = forms.IntegerField(initial=0, min_value=-3, max_value=2)

    def get_value(self) -> str:
        key = self.cleaned_data["pushover_user_key"]
        prio = self.cleaned_data["prio"]
        prio_up = self.cleaned_data["prio_up"]
        return "%s|%s|%s" % (key, prio, prio_up)
