from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from hc.checks.models import Canary

@login_required
def checks(request):

    canaries = Canary.objects.filter(user=request.user)

    ctx = {
        "canaries": canaries
    }

    return render(request, "checks/index.html", ctx)
