from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from hc.api.models import Check
from hc.front.forms import TimeoutForm, TIMEOUT_CHOICES


def index(request):
    ctx = {
        "page": "welcome"
    }

    return render(request, "index.html", ctx)


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
    check.name = request.POST["name"]
    check.save()

    return redirect("hc-checks")


@login_required
def update_timeout(request, code):
    assert request.method == "POST"

    form = TimeoutForm(request.POST)
    if form.is_valid():
        check = Check.objects.get(code=code)
        check.timeout = form.cleaned_data["timeout"]
        check.save()

    return redirect("hc-checks")
