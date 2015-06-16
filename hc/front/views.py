from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from hc.api.models import Check


def index(request):
    return render(request, "index.html")


@login_required
def checks(request):

    checks = Check.objects.filter(user=request.user).order_by("created")

    ctx = {
        "checks": checks
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
