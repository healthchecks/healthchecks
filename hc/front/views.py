from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from hc.api.models import Check

@login_required
def checks(request):

    checks = Check.objects.filter(user=request.user)

    ctx = {
        "checks": checks
    }

    return render(request, "checks/index.html", ctx)
