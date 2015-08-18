from datetime import timedelta as td

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from hc.api.decorators import uuid_or_400
from hc.api.models import Channel, Check, Ping
from hc.front.forms import AddChannelForm, TimeoutForm


@login_required
def my_checks(request):
    checks = Check.objects.filter(user=request.user).order_by("created")

    ctx = {
        "page": "checks",
        "checks": checks,
        "now": timezone.now()
    }

    return render(request, "front/my_checks.html", ctx)


def index(request):
    if request.user.is_authenticated():
        return redirect("hc-checks")

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


def pricing(request):
    return render(request, "front/pricing.html", {"page": "pricing"})


def docs(request):
    if "welcome_code" in request.session:
        code = request.session["welcome_code"]
        check = Check.objects.get(code=code)
    else:
        check = Check(code="uuid-goes-here")

    ctx = {
        "page": "docs",
        "ping_endpoint": settings.PING_ENDPOINT,
        "check": check,
        "ping_url": check.url()
    }

    return render(request, "front/docs.html", ctx)


def about(request):
    return render(request, "front/about.html", {"page": "about"})


@login_required
def add_check(request):
    assert request.method == "POST"

    check = Check(user=request.user)
    check.save()

    check.assign_all_channels()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def update_name(request, code):
    assert request.method == "POST"

    check = get_object_or_404(Check, code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    check.name = request.POST["name"]
    check.save()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def update_timeout(request, code):
    assert request.method == "POST"

    check = get_object_or_404(Check, code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    form = TimeoutForm(request.POST)
    if form.is_valid():
        check.timeout = td(seconds=form.cleaned_data["timeout"])
        check.grace = td(seconds=form.cleaned_data["grace"])
        check.save()

    return redirect("hc-checks")


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
def remove_check(request, code):
    assert request.method == "POST"

    check = get_object_or_404(Check, code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    check.delete()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def log(request, code):
    check = get_object_or_404(Check, code=code)
    if check.user != request.user:
        return HttpResponseForbidden()

    pings = Ping.objects.filter(owner=check).order_by("-created")[:100]

    ctx = {
        "check": check,
        "pings": pings

    }

    return render(request, "front/log.html", ctx)


@login_required
def channels(request):
    if request.method == "POST":
        code = request.POST["channel"]
        try:
            channel = Channel.objects.get(code=code)
        except Channel.DoesNotExist:
            return HttpResponseBadRequest()
        if channel.user != request.user:
            return HttpResponseForbidden()

        new_checks = []
        for key in request.POST:
            if key.startswith("check-"):
                code = key[6:]
                try:
                    check = Check.objects.get(code=code)
                except Check.DoesNotExist:
                    return HttpResponseBadRequest()
                if check.user != request.user:
                    return HttpResponseForbidden()
                new_checks.append(check)

        channel.checks = new_checks
        return redirect("hc-channels")

    channels = Channel.objects.filter(user=request.user).order_by("created")
    num_checks = Check.objects.filter(user=request.user).count()

    ctx = {
        "page": "channels",
        "channels": channels,
        "num_checks": num_checks

    }
    return render(request, "front/channels.html", ctx)


@login_required
def add_channel(request):
    assert request.method == "POST"
    form = AddChannelForm(request.POST)
    if form.is_valid():
        channel = form.save(commit=False)
        channel.user = request.user
        channel.save()

        checks = Check.objects.filter(user=request.user)
        channel.checks.add(*checks)

        if channel.kind == "email":
            channel.send_verify_link()

        return redirect("hc-channels")
    else:
        return HttpResponseBadRequest()


@login_required
@uuid_or_400
def channel_checks(request, code):
    channel = get_object_or_404(Channel, code=code)
    if channel.user != request.user:
        return HttpResponseForbidden()

    assigned = set([check.code for check in channel.checks.all()])
    checks = Check.objects.filter(user=request.user).order_by("created")

    ctx = {
        "checks": checks,
        "assigned": assigned,
        "channel": channel
    }

    return render(request, "front/channel_checks.html", ctx)


@uuid_or_400
def verify_email(request, code, token):
    channel = get_object_or_404(Channel, code=code)
    if channel.make_token() == token:
        channel.email_verified = True
        channel.save()
        return render(request, "front/verify_email_success.html")

    return render(request, "bad_link.html")


@login_required
@uuid_or_400
def remove_channel(request, code):
    assert request.method == "POST"

    channel = get_object_or_404(Channel, code=code)
    if channel.user != request.user:
        return HttpResponseForbidden()

    channel.delete()

    return redirect("hc-channels")
