from datetime import timedelta as td

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from hc.api.decorators import uuid_or_400
from hc.api.models import Check, Ping
from hc.front.forms import TimeoutForm


def _welcome(request):
    if "welcome_code" not in request.session:
        check = Check()
        check.save()
        code = str(check.code)
        request.session["welcome_code"] = code
    else:
        code = request.session["welcome_code"]
        check = Check.objects.get(code=code)

    ctx = {
        "page": "welcome",
        "check": check,
        "ping_url": check.url()
    }

    return render(request, "front/welcome.html", ctx)


def _my_checks(request):
    checks = Check.objects.filter(user=request.user).order_by("created")

    ctx = {
        "checks": checks,
        "now": timezone.now()
    }

    return render(request, "front/my_checks.html", ctx)


def index(request):
    if request.user.is_authenticated():
        return _my_checks(request)
    else:
        return _welcome(request)


def pricing(request):
    return render(request, "front/pricing.html", {"page": "pricing"})


def docs(request):
    ctx = {
        "page": "docs",
        "ping_endpoint": settings.PING_ENDPOINT
    }

    return render(request, "front/docs.html", ctx)


def about(request):
    return render(request, "front/about.html", {"page": "about"})


@login_required
def add_check(request):
    assert request.method == "POST"

    check = Check(user=request.user)
    check.save()
    return redirect("hc-index")


@login_required
@uuid_or_400
def update_name(request, code):
    assert request.method == "POST"

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    check.name = request.POST["name"]
    check.save()

    return redirect("hc-index")


@login_required
@uuid_or_400
def update_timeout(request, code):
    assert request.method == "POST"

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    form = TimeoutForm(request.POST)
    if form.is_valid():
        check.timeout = td(seconds=form.cleaned_data["timeout"])
        check.grace = td(seconds=form.cleaned_data["grace"])
        check.save()

    return redirect("hc-index")


@login_required
@uuid_or_400
def email_preview(request, code):
    """ A debug view to see how email will look.

    Will keep it around until I'm happy with email stying.

    """

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    ctx = {
        "check": check,
        "checks": check.user.check_set.all(),
        "now": timezone.now()

    }

    return render(request, "emails/alert/body.html", ctx)


@login_required
@uuid_or_400
def remove(request, code):
    assert request.method == "POST"

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    check.delete()

    return redirect("hc-index")


@login_required
@uuid_or_400
def log(request, code):

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    pings = Ping.objects.filter(owner=check).order_by("-created")[:100]

    ctx = {
        "check": check,
        "pings": pings

    }

    return render(request, "front/log.html", ctx)
