from datetime import timedelta as td
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from hc.api.models import TokenBucket


class LowercaseEmailField(forms.EmailField):
    def clean(self, value):
        value = super(LowercaseEmailField, self).clean(value)
        return value.lower()


class AvailableEmailForm(forms.Form):
    # Call it "identity" instead of "email"
    # to avoid some of the dumber bots
    identity = LowercaseEmailField(
        error_messages={"required": "Please enter your email address."}
    )

    def clean_identity(self):
        v = self.cleaned_data["identity"]
        if User.objects.filter(email=v).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return v


class EmailLoginForm(forms.Form):
    # Call it "identity" instead of "email"
    # to avoid some of the dumber bots
    identity = LowercaseEmailField()

    def clean_identity(self):
        v = self.cleaned_data["identity"]
        if not TokenBucket.authorize_login_email(v):
            raise forms.ValidationError("Too many attempts, please try later.")

        try:
            self.user = User.objects.get(email=v)
        except User.DoesNotExist:
            raise forms.ValidationError("Incorrect email address.")

        return v


class PasswordLoginForm(forms.Form):
    email = LowercaseEmailField()
    password = forms.CharField()

    def clean(self):
        username = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")

        if username and password:
            if not TokenBucket.authorize_login_password(username):
                raise forms.ValidationError("Too many attempts, please try later.")

            self.user = authenticate(username=username, password=password)
            if self.user is None or not self.user.is_active:
                raise forms.ValidationError("Incorrect email or password.")

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
    password = forms.CharField(min_length=8)


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


class ProjectNameForm(forms.Form):
    name = forms.CharField(max_length=200, required=True)
