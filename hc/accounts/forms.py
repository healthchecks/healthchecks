import base64
import binascii
from datetime import timedelta as td

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from hc.accounts.models import REPORT_CHOICES
from hc.api.models import TokenBucket


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


class AvailableEmailForm(forms.Form):
    # Call it "identity" instead of "email"
    # to avoid some of the dumber bots
    identity = LowercaseEmailField(
        error_messages={"required": "Please enter your email address."}
    )

    def clean_identity(self):
        v = self.cleaned_data["identity"]
        if len(v) > 254:
            raise forms.ValidationError("Address is too long.")

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
    email = LowercaseEmailField(max_length=254)
    rw = forms.BooleanField(required=False)


class RemoveTeamMemberForm(forms.Form):
    email = LowercaseEmailField()


class ProjectNameForm(forms.Form):
    name = forms.CharField(max_length=60)


class TransferForm(forms.Form):
    email = LowercaseEmailField()


class AddCredentialForm(forms.Form):
    name = forms.CharField(max_length=100)
    client_data_json = Base64Field()
    attestation_object = Base64Field()


class WebAuthnForm(forms.Form):
    credential_id = Base64Field()
    client_data_json = Base64Field()
    authenticator_data = Base64Field()
    signature = Base64Field()
