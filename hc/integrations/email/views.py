from __future__ import annotations

from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.views import _get_rw_project_for_user
from hc.integrations.email import forms


def email_form(request: AuthenticatedHttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.EmailForm(request.POST)
        if form.is_valid():
            if channel.disabled or form.cleaned_data["value"] != channel.email.value:
                channel.disabled = False

                if not settings.EMAIL_USE_VERIFICATION:
                    # In self-hosted setting, administrator can set
                    # EMAIL_USE_VERIFICATION=False to disable email verification
                    channel.email_verified = True
                elif form.cleaned_data["value"] == request.user.email:
                    # If the user is adding *their own* address
                    # we skip the verification step
                    channel.email_verified = True
                else:
                    channel.email_verified = False

            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()

            if not channel.email_verified:
                channel.send_verify_link()

            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.EmailForm()
    else:
        form = forms.EmailForm(
            {
                "value": channel.email.value,
                "up": channel.email.notify_up,
                "down": channel.email.notify_down,
            }
        )

    ctx = {
        "page": "channels",
        "project": channel.project,
        "use_verification": settings.EMAIL_USE_VERIFICATION,
        "form": form,
        "is_new": adding,
    }
    return render(request, "email_form.html", ctx)


@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="email")
    return email_form(request, channel)


def verify(request: HttpRequest, code: UUID, token: str) -> HttpResponse:
    channel = get_object_or_404(Channel, code=code)
    if channel.make_token() == token:
        channel.email_verified = True
        channel.save()
        return render(request, "front/verify_email_success.html")

    return render(request, "bad_link.html")


@csrf_exempt
def unsubscribe(request: HttpRequest, code: UUID, signed_token: str) -> HttpResponse:
    ctx = {}

    # Some email servers open links in emails to check for malicious content.
    # To work around this, on GET requests we serve a confirmation form.
    # If the signature is at least 5 minutes old, we also include JS code to
    # auto-submit the form.
    signer = signing.TimestampSigner(salt="alerts")

    # First, check the signature without looking at the timestamp:
    try:
        token = signer.unsign(signed_token)
    except signing.BadSignature:
        return render(request, "bad_link.html")

    # Then, check if timestamp is older than 5 minutes:
    try:
        signer.unsign(signed_token, max_age=300)
    except signing.SignatureExpired:
        ctx["autosubmit"] = True

    channel = get_object_or_404(Channel, code=code, kind="email")
    if channel.make_token() != token:
        return render(request, "bad_link.html")

    if request.method != "POST":
        return render(request, "accounts/unsubscribe_submit.html", ctx)

    channel.delete()
    return render(request, "front/unsubscribe_success.html")
