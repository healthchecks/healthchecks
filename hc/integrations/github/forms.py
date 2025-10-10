from __future__ import annotations

from django import forms


class AddGitHubForm(forms.Form):
    repo_name = forms.CharField(max_length=500)
    labels = forms.CharField(max_length=500, required=False)

    def get_labels(self) -> list[str]:
        result = []

        for part in self.cleaned_data["labels"].split(","):
            part = part.strip()
            if part != "":
                result.append(part)

        return result
