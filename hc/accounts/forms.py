from datetime import timedelta as td
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User


class LowercaseEmailField(forms.EmailField):

    def clean(self, value):
        value = super(LowercaseEmailField, self).clean(value)
        return value.lower()


class EmailForm(forms.Form):
    # Call it "identity" instead of "email"
    # to avoid some of the dumber bots
    identity = LowercaseEmailField()

    def clean_identity(self):
        v = self.cleaned_data["identity"]

        # If registration is not open then validate if an user
        # account with this address exists-
        if not settings.REGISTRATION_OPEN:
            if not User.objects.filter(email=v).exists():
                raise forms.ValidationError("Incorrect email address.")

        return v


class EmailPasswordForm(forms.Form):
    email = LowercaseEmailField()
    password = forms.CharField()

    def clean(self):
        username = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user = authenticate(username=username, password=password)
            if self.user is None:
                raise forms.ValidationError("Incorrect email or password")
            if not self.user.is_active:
                raise forms.ValidationError("Account is inactive")

        return self.cleaned_data


class ReportSettingsForm(forms.Form):
    reports_allowed = forms.BooleanField(required=False)
    nag_period = forms.IntegerField(min_value=0, max_value=86400)

    def clean_nag_period(self):
        seconds = self.cleaned_data["nag_period"]

        if seconds not in (0, 3600, 86400):
            raise forms.ValidationError("Bad nag_period: %d" % seconds)

        return td(seconds=seconds)


class SetPasswordForm(forms.Form):
    password = forms.CharField()


class ChangeEmailForm(forms.Form):
    error_css_class = "has-error"
    email = LowercaseEmailField()

    def clean_email(self):
        v = self.cleaned_data["email"]
        if User.objects.filter(email=v).exists():
            raise forms.ValidationError("%s is already registered" % v)

        return v


class InviteTeamMemberForm(forms.Form):
    email = LowercaseEmailField()


class RemoveTeamMemberForm(forms.Form):
    email = LowercaseEmailField()


class TeamNameForm(forms.Form):
    team_name = forms.CharField(max_length=200, required=True)
