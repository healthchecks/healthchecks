from __future__ import annotations

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front import forms
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user


@require_setting("SPIKE_ENABLED")
@login_required
def add_spike(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="spike")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "add_spike.html", ctx)
