from __future__ import annotations

from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front import forms
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user


@require_setting("TWILIO_AUTH")
def sms_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.PhoneUpDownForm(request.POST)
        if form.is_valid():
            channel.name = form.cleaned_data["label"]
            channel.value = form.get_json()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.PhoneUpDownForm(initial={"up": False})
    else:
        form = forms.PhoneUpDownForm(
            {
                "label": channel.name,
                "phone": channel.phone.value,
                "up": channel.phone.notify_up,
                "down": channel.phone.notify_down,
            }
        )

    ctx = {
        "page": "channels",
        "project": channel.project,
        "twilio_from": settings.TWILIO_FROM,
        "form": form,
        "profile": channel.project.owner_profile,
        "is_new": adding,
    }
    return render(request, "sms_form.html", ctx)


@require_setting("TWILIO_AUTH")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="sms")
    return sms_form(request, channel)
