from __future__ import annotations

import secrets
from functools import wraps
from typing import Any

from django.core.signing import SignatureExpired, TimestampSigner
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from hc.api.models import TokenBucket
from hc.lib import emails
from hc.lib.typealias import ViewFunc


def _session_unsign(request: HttpRequest, key: str, max_age: int) -> str | None:
    if key not in request.session:
        return None

    try:
        return TimestampSigner().unsign(request.session[key], max_age=max_age)
    except SignatureExpired:
        return None


def require_sudo_mode(f: ViewFunc) -> ViewFunc:
    @wraps(f)
    def wrapper(request: HttpRequest, *args: Any, **kwds: Any) -> HttpResponse:
        assert request.user.is_authenticated

        # is sudo mode active and has not expired yet?
        if _session_unsign(request, "sudo", 1800) == "active":
            return f(request, *args, **kwds)

        if not TokenBucket.authorize_sudo_code(request.user):
            return render(request, "try_later.html")

        # has the user submitted a code to enter sudo mode?
        if "sudo_code" in request.POST:
            ours = _session_unsign(request, "sudo_code", 900)
            if ours and ours == request.POST["sudo_code"]:
                request.session.pop("sudo_code")
                request.session["sudo"] = TimestampSigner().sign("active")
                return redirect(request.path)

        if not _session_unsign(request, "sudo_code", 900):
            code = "%06d" % secrets.randbelow(1000000)
            request.session["sudo_code"] = TimestampSigner().sign(code)
            emails.sudo_code(request.user.email, {"sudo_code": code})

        ctx = {}
        if "sudo_code" in request.POST:
            ctx["wrong_code"] = True

        return render(request, "accounts/sudo.html", ctx)

    return wrapper
