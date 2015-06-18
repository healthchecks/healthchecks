from datetime import timedelta as td

from django import forms

TIMEOUT_CHOICES = (
    ("15 minutes", td(minutes=15)),
    ("30 minutes", td(minutes=30)),
    ("1 hour", td(hours=1)),
    ("3 hours", td(hours=3)),
    ("6 hours", td(hours=6)),
    ("12 hours", td(hours=12)),
    ("1 day", td(days=1)),
    ("2 days", td(days=2)),
    ("3 days", td(days=3)),
    ("1 week", td(weeks=1))
)


class TimeoutForm(forms.Form):
    timeout = forms.ChoiceField(choices=TIMEOUT_CHOICES)
