from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from hc.api.models import Check


def index(request):
    return render(request, "index.html")


@login_required
def checks(request):

    checks = Check.objects.filter(user=request.user)

    ctx = {
        "checks": checks
    }

    return render(request, "front/index.html", ctx)
