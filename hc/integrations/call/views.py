from __future__ import annotations

from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front import forms
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user


@require_setting("TWILIO_AUTH")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.PhoneNumberForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="call")
            channel.name = form.cleaned_data["label"]
            channel.value = form.get_json()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.PhoneNumberForm()

    ctx = {
        "page": "channels",
        "project": project,
        "twilio_from": settings.TWILIO_FROM,
        "form": form,
        "profile": project.owner_profile,
    }
    return render(request, "add_call.html", ctx)
