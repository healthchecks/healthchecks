from __future__ import annotations

import json
import uuid
from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel, TokenBucket
from hc.api.transports import TransportError
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.integrations.signal import forms
from hc.integrations.signal.transport import Signal, SignalRateLimitFailure


@require_setting("SIGNAL_CLI_SOCKET")
def signal_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.SignalForm(request.POST)
        if form.is_valid():
            channel.name = form.cleaned_data["label"]
            channel.value = form.get_json()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.SignalForm()
    else:
        form = forms.SignalForm(
            {
                "label": channel.name,
                "recipient": channel.phone.value,
                "up": channel.phone.notify_up,
                "down": channel.phone.notify_down,
            }
        )

    ctx = {
        "page": "channels",
        "project": channel.project,
        "form": form,
        "is_new": adding,
    }
    return render(request, "signal_form.html", ctx)


@require_setting("SIGNAL_CLI_SOCKET")
@login_required
def add_signal(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="signal")
    return signal_form(request, channel)


@require_setting("SIGNAL_CLI_SOCKET")
@login_required
def signal_captcha(request: AuthenticatedHttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    ctx = {"challenge": request.GET.get("challenge", "")}
    if request.method == "POST":
        challenge = request.POST.get("challenge", "")
        captcha = request.POST.get("captcha", "")
        if captcha.startswith("signalcaptcha://"):
            captcha = captcha[16:]

        payload = {
            "jsonrpc": "2.0",
            "method": "submitRateLimitChallenge",
            "params": {"challenge": str(challenge), "captcha": captcha},
            "id": str(uuid.uuid4()),
        }

        payload_bytes = (json.dumps(payload) + "\n").encode()
        for reply_bytes in Signal._read_replies(payload_bytes):
            try:
                reply = json.loads(reply_bytes.decode())
            except ValueError:
                ctx["result"] = "submitRateLimitChallenge failed"
                break

            if reply.get("id") == payload["id"]:
                ctx["result"] = reply_bytes.decode()
                break

    return render(request, "front/signal_captcha.html", ctx)


@require_setting("SIGNAL_CLI_SOCKET")
@login_required
@require_POST
def verify_signal_number(request: AuthenticatedHttpRequest) -> HttpResponse:
    def render_result(result: str | None) -> HttpResponse:
        return render(request, "signal_result.html", {"result": result})

    # Enforce per-account rate limit (50 verifications per day)
    if not TokenBucket.authorize_signal_verification(request.user):
        return render_result("Verification rate limit exceeded")

    form = forms.SignalRecipientForm(request.POST)
    if not form.is_valid():
        return render_result("Invalid phone number")

    recipient = form.cleaned_data["recipient"]
    # Enforce per-recipient rate limit (6 messages per minute)
    if not TokenBucket.authorize_signal(recipient):
        return render_result("Verification rate limit exceeded")

    try:
        Signal.send(recipient, f"Test message from {settings.SITE_NAME}")
    except SignalRateLimitFailure as e:
        Channel().send_signal_captcha_alert(e.token, e.reply.decode())
        return render_result(e.message)
    except TransportError as e:
        return render_result(e.message)

    # Success!
    return render_result(None)
