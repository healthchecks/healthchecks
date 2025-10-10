from __future__ import annotations

from typing import Any

from django import forms


class GroupForm(forms.Form):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        project = kwargs.pop("project")
        super().__init__(*args, **kwargs)

        assert isinstance(self.fields["channels"], forms.MultipleChoiceField)
        self.fields["channels"].choices = (
            (c.code, c) for c in project.channel_set.exclude(kind="group")
        )

    error_css_class = "has-error"
    label = forms.CharField(max_length=100, required=False)
    channels = forms.MultipleChoiceField()

    def get_value(self) -> str:
        return ",".join(self.cleaned_data["channels"])
