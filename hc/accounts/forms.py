from __future__ import annotations

from datetime import timedelta as td
from typing import Any

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpRequest
from pyotp.totp import TOTP

from hc.accounts.models import REPORT_CHOICES, Member
from hc.api.models import TokenBucket
from hc.lib.tz import all_timezones


class LowercaseEmailField(forms.EmailField):
    def clean(self, value: str) -> str:
        value = super(LowercaseEmailField, self).clean(value)
        return value.lower()


class SignupForm(forms.Form):
    # Call it "identity" instead of "email"
    # to avoid some of the dumber bots
    identity = LowercaseEmailField(
        error_messages={"required": "Please enter your email address."}
    )
    tz = forms.CharField(required=False)

    def __init__(self, request: HttpRequest):
        self.request = request
        super(SignupForm, self).__init__(request.POST)

    def clean_identity(self) -> str:
        if not TokenBucket.authorize_auth_ip(self.request):
            raise forms.ValidationError("Too many attempts, please try later.")

        v = self.cleaned_data["identity"]
        assert isinstance(v, str)
        if len(v) > 254:
            raise forms.ValidationError("Address is too long.")

        return v

    def clean_tz(self) -> str | None:
        assert isinstance(self.cleaned_data["tz"], str)

        # Declare tz as "clean" only if we can find it in hc.lib.tz.all_timezones
        if self.cleaned_data["tz"] in all_timezones:
            return self.cleaned_data["tz"]

        # Otherwise, return None, and *don't* throw a validation exception:
        # If user's browser reports a timezone we don't recognize, we
        # should ignore the timezone but still save the rest of the form.
        return None


class EmailLoginForm(forms.Form):
    # Call it "identity" instead of "email"
    # to avoid some of the dumber bots
    identity = LowercaseEmailField()

    def __init__(self, request: HttpRequest | None = None):
        self.request = request
        super(EmailLoginForm, self).__init__(request.POST if request else None)

    def clean_identity(self) -> str:
        v = self.cleaned_data["identity"]

        assert isinstance(v, str)
        if not TokenBucket.authorize_login_email(v):
            raise forms.ValidationError("Too many attempts, please try later.")

        assert self.request
        if not TokenBucket.authorize_auth_ip(self.request):
            raise forms.ValidationError("Too many attempts, please try later.")

        self.user: User | None
        try:
            self.user = User.objects.get(email=v)
        except User.DoesNotExist:
            self.user = None

        return v


class PasswordLoginForm(forms.Form):
    email = LowercaseEmailField()
    password = forms.CharField()

    def clean(self) -> dict[str, Any]:
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
    reports = forms.ChoiceField(choices=REPORT_CHOICES)
    nag_period = forms.IntegerField(min_value=0, max_value=86400)
    tz = forms.CharField()

    def clean_nag_period(self) -> td:
        seconds = self.cleaned_data["nag_period"]

        if seconds not in (0, 3600, 86400):
            raise forms.ValidationError("Bad nag_period: %d" % seconds)

        return td(seconds=seconds)

    def clean_tz(self) -> str | None:
        assert isinstance(self.cleaned_data["tz"], str)

        # Declare tz as "clean" only if we can find it in hc.lib.tz.all_timezones
        if self.cleaned_data["tz"] in all_timezones:
            return self.cleaned_data["tz"]

        # Otherwise, return None, and *don't* throw a validation exception:
        # If user's browser reports a timezone we don't recognize, we
        # should ignore the timezone but still save the rest of the form.
        return None


class SetPasswordForm(forms.Form):
    password = forms.CharField(min_length=8)


class ChangeEmailForm(forms.Form):
    error_css_class = "has-error"
    email = LowercaseEmailField()

    def clean_email(self) -> str:
        v = self.cleaned_data["email"]
        assert isinstance(v, str)
        if User.objects.filter(email=v).exists():
            raise forms.ValidationError("%s is already registered" % v)

        return v


class InviteTeamMemberForm(forms.Form):
    email = LowercaseEmailField(max_length=254)
    role = forms.ChoiceField(choices=Member.Role.choices)


class RemoveTeamMemberForm(forms.Form):
    email = LowercaseEmailField()


class ProjectNameForm(forms.Form):
    name = forms.CharField(max_length=60)


class TransferForm(forms.Form):
    email = LowercaseEmailField()


class AddWebAuthnForm(forms.Form):
    name = forms.CharField(max_length=100)
    response = forms.CharField()


class WebAuthnForm(forms.Form):
    response = forms.CharField()


class TotpForm(forms.Form):
    error_css_class = "has-error"
    code = forms.RegexField(regex=r"^\d{6}$")

    def __init__(self, totp: TOTP, post: Any = None):
        self.totp = totp
        super(TotpForm, self).__init__(post)

    def clean_code(self) -> str:
        assert isinstance(self.cleaned_data["code"], str)
        if not self.totp.verify(self.cleaned_data["code"], valid_window=1):
            raise forms.ValidationError("The code you entered was incorrect.")

        return self.cleaned_data["code"]
