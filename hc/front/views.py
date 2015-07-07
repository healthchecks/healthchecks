from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from hc.api.models import Check
from hc.front.forms import TimeoutForm, TIMEOUT_CHOICES


def index(request):
    if "welcome_code" not in request.session:
        check = Check()
        check.save()
        code = str(check.code)
        request.session["welcome_code"] = code
    else:
        code = request.session["welcome_code"]
        check = Check.objects.get(code=code)

    if check.alert_after:
        duration = check.alert_after - timezone.now()
        timer = int(duration.total_seconds())
        timer_formatted = "%dh %dm %ds" % (timer / 3600, (timer / 60) % 60, timer % 60)
    else:
        timer = 0
        timer_formatted = "Never"

    ctx = {
        "page": "welcome",
        "check": check,
        "timer": timer,
        "timer_formatted": timer_formatted,
        "ping_url": check.url()
    }

    return render(request, "index.html", ctx)


def pricing(request):
    return render(request, "pricing.html", {"page": "pricing"})


def docs(request):
    return render(request, "docs.html", {"page": "docs"})


def about(request):
    return render(request, "about.html", {"page": "about"})


@login_required
def checks(request):
    checks = Check.objects.filter(user=request.user).order_by("created")

    ctx = {
        "checks": checks,
        "now": timezone.now,
        "timeout_choices": TIMEOUT_CHOICES,
        "page": "checks"
    }

    return render(request, "front/index.html", ctx)


@login_required
def add_check(request):
    assert request.method == "POST"

    check = Check(user=request.user)
    check.save()
    return redirect("hc-checks")


@login_required
def update_name(request, code):
    assert request.method == "POST"

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    check.name = request.POST["name"]
    check.save()

    return redirect("hc-checks")


@login_required
def update_timeout(request, code):
    assert request.method == "POST"

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    form = TimeoutForm(request.POST)
    if form.is_valid():
        check.timeout = form.cleaned_data["timeout"]
        check.save()

    return redirect("hc-checks")
