from __future__ import annotations

import json

from django import forms
from django.core.exceptions import ValidationError
from hc.front.forms import LaxURLField, _choices


def _is_latin1(s: str) -> bool:
    try:
        s.encode("latin-1")
        return True
    except UnicodeError:
        return False


class HeadersField(forms.Field):
    message = """Use "Header-Name: value" pairs, one per line."""

    def to_python(self, value: str | None) -> dict[str, str]:
        if not value:
            return {}

        headers = {}
        for line in value.split("\n"):
            if not line.strip():
                continue

            if ":" not in line:
                raise ValidationError(self.message)

            n, v = line.split(":", maxsplit=1)
            n, v = n.strip(), v.strip()
            if not n or not v:
                raise ValidationError(message=self.message)

            if not _is_latin1(n):
                raise ValidationError(
                    message="Header names must not contain special characters"
                )

            headers[n] = v

        return headers

    def validate(self, value: dict[str, str]) -> None:
        super().validate(value)
        for k, v in value.items():
            if len(k) > 1000 or len(v) > 1000:
                raise ValidationError("Value too long")


class WebhookForm(forms.Form):
    error_css_class = "has-error"
    name = forms.CharField(max_length=100, required=False)

    method_down = forms.ChoiceField(initial="GET", choices=_choices("GET,POST,PUT"))
    body_down = forms.CharField(max_length=1000, required=False)
    headers_down = HeadersField(required=False)
    url_down = LaxURLField(max_length=1000, required=False, assume_scheme="https")

    method_up = forms.ChoiceField(initial="GET", choices=_choices("GET,POST,PUT"))
    body_up = forms.CharField(max_length=1000, required=False)
    headers_up = HeadersField(required=False)
    url_up = LaxURLField(max_length=1000, required=False, assume_scheme="https")

    def clean(self) -> None:
        super().clean()

        url_down = self.cleaned_data.get("url_down")
        url_up = self.cleaned_data.get("url_up")

        if not url_down and not url_up:
            if not self.has_error("url_down"):
                self.add_error("url_down", "Enter a valid URL.")

    def get_value(self) -> str:
        return json.dumps(dict(self.cleaned_data), sort_keys=True)
