import base64
import binascii
from datetime import timedelta as td

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from hc.accounts.models import REPORT_CHOICES, Member
from hc.api.models import TokenBucket
import pytz


class LowercaseEmailField(forms.EmailField):
    def clean(self, value):
        value = super(LowercaseEmailField, self).clean(value)
        return value.lower()


class Base64Field(forms.CharField):
    def to_python(self, value):
        if value is None:
            return None

        try:
            return base64.b64decode(value.encode())
        except binascii.Error:
            raise ValidationError(message="Cannot decode base64")


class SignupForm(forms.Form):
    # Call it "identity" instead of "email"
    # to avoid some of the dumber bots
    identity = LowercaseEmailField(
        error_messages={"required": "Please enter your email address."}
    )
    tz = forms.CharField(required=False)

    def clean_identity(self):
        v = self.cleaned_data["identity"]
        if len(v) > 254:
            raise forms.ValidationError("Address is too long.")

        if User.objects.filter(email=v).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return v

    def clean_tz(self):
        # Declare tz as "clean" only if we can find it in pytz.all_timezones
        if self.cleaned_data["tz"] in pytz.all_timezones:
            return self.cleaned_data["tz"]

        # Otherwise, return None, and *don't* throw a validation exception:
        # If user's browser reports a timezone we don't recognize, we
        # should ignore the timezone but still save the rest of the form.


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
            raise forms.ValidationError("Unknown email address.")

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
    reports = forms.ChoiceField(choices=REPORT_CHOICES)
    nag_period = forms.IntegerField(min_value=0, max_value=86400)
    tz = forms.CharField()

    def clean_nag_period(self):
        seconds = self.cleaned_data["nag_period"]

        if seconds not in (0, 3600, 86400):
            raise forms.ValidationError("Bad nag_period: %d" % seconds)

        return td(seconds=seconds)

    def clean_tz(self):
        # Declare tz as "clean" only if we can find it in pytz.all_timezones
        if self.cleaned_data["tz"] in pytz.all_timezones:
            return self.cleaned_data["tz"]

        # Otherwise, return None, and *don't* throw a validation exception:
        # If user's browser reports a timezone we don't recognize, we
        # should ignore the timezone but still save the rest of the form.


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
    client_data_json = Base64Field()
    attestation_object = Base64Field()


class WebAuthnForm(forms.Form):
    credential_id = Base64Field()
    client_data_json = Base64Field()
    authenticator_data = Base64Field()
    signature = Base64Field()


class TotpForm(forms.Form):
    error_css_class = "has-error"
    code = forms.RegexField(regex=r"^\d{6}$")

    def __init__(self, totp, post=None, files=None):
        self.totp = totp
        super(TotpForm, self).__init__(post, files)

    def clean_code(self):
        if not self.totp.verify(self.cleaned_data["code"], valid_window=1):
            raise forms.ValidationError("The code you entered was incorrect.")

        return self.cleaned_data["code"]
