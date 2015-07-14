from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from hc.api.models import Check
from hc.front.forms import TimeoutForm, TIMEOUT_CHOICES


def _welcome(request):
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

    return render(request, "front/welcome.html", ctx)


def _my_checks(request):
    checks = Check.objects.filter(user=request.user).order_by("created")

    ctx = {
        "checks": checks,
        "now": timezone.now(),
        "timeout_choices": TIMEOUT_CHOICES
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
    return render(request, "front/docs.html", {"page": "docs"})


def about(request):
    return render(request, "front/about.html", {"page": "about"})


@login_required
def add_check(request):
    assert request.method == "POST"

    check = Check(user=request.user)
    check.save()
    return redirect("hc-index")


@login_required
def update_name(request, code):
    assert request.method == "POST"

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    check.name = request.POST["name"]
    check.save()

    return redirect("hc-index")


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

    return redirect("hc-index")


@login_required
def email_preview(request, code):
    """ A debug view to see how email will look.

    Will keep it around until I'm happy with email stying.

    """

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    from hc.api.models import TIMEOUT_CHOICES
    ctx = {
        "check": check,
        "checks": check.user.check_set.all(),
        "timeout_choices": TIMEOUT_CHOICES,
        "now": timezone.now()

    }

    return render(request, "emails/alert/body.html", ctx)


@login_required
def remove(request, code):
    assert request.method == "POST"

    check = Check.objects.get(code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    check.delete()

    return redirect("hc-index")
