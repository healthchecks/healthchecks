from collections import Counter
from datetime import timedelta as td

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.six.moves.urllib.parse import urlencode
from hc.accounts.models import Profile
from hc.api.decorators import uuid_or_400
from hc.api.models import Channel, Check, Ping
from hc.front.forms import AddChannelForm, NameTagsForm, TimeoutForm


@login_required
def my_checks(request):
    checks = Check.objects.filter(user=request.user).order_by("created")

    counter = Counter()
    down_tags, grace_tags = set(), set()
    for check in checks:
        status = check.get_status()
        for tag in check.tags_list():
            if tag == "":
                continue

            counter[tag] += 1

            if status == "down":
                down_tags.add(tag)
            elif status == "grace":
                grace_tags.add(tag)

    ctx = {
        "page": "checks",
        "checks": checks,
        "now": timezone.now(),
        "tags": counter.most_common(),
        "down_tags": down_tags,
        "grace_tags": grace_tags
    }

    return render(request, "front/my_checks.html", ctx)


def index(request):
    if request.user.is_authenticated():
        return redirect("hc-checks")

    check = None
    if "welcome_code" in request.session:
        code = request.session["welcome_code"]
        check = Check.objects.filter(code=code).first()

    if check is None:
        check = Check()
        check.save()
        code = str(check.code)
        request.session["welcome_code"] = code

    ctx = {
        "page": "welcome",
        "check": check,
        "ping_url": check.url()
    }

    return render(request, "front/welcome.html", ctx)


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
    if check.user_id != request.user.id:
        return HttpResponseForbidden()

    form = NameTagsForm(request.POST)
    if form.is_valid():
        check.name = form.cleaned_data["name"]
        check.tags = form.cleaned_data["tags"]
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

    profile = Profile.objects.for_user(request.user)
    limit = profile.ping_log_limit
    pings = Ping.objects.filter(owner=check).order_by("-created")[:limit]

    # Now go through pings, calculate time gaps, and decorate
    # the pings list for convenient use in template
    wrapped = []
    now = timezone.now()
    for i, ping in enumerate(pings):
        prev = now if i == 0 else pings[i - 1].created

        duration = prev - ping.created
        if duration > check.timeout:
            downtime = {"prev_date": prev, "date": ping.created}
            if i > 0:
                wrapped[-1]["status"] = "late"

            if duration > check.timeout + check.grace:
                downtime["down"] = True
                if i > 0:
                    wrapped[-1]["status"] = "down"

            wrapped.append(downtime)

        wrapped.append({"ping": ping})

    ctx = {
        "check": check,
        "pings": wrapped
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
        if channel.user_id != request.user.id:
            return HttpResponseForbidden()

        new_checks = []
        for key in request.POST:
            if key.startswith("check-"):
                code = key[6:]
                try:
                    check = Check.objects.get(code=code)
                except Check.DoesNotExist:
                    return HttpResponseBadRequest()
                if check.user_id != request.user.id:
                    return HttpResponseForbidden()
                new_checks.append(check)

        channel.checks = new_checks
        return redirect("hc-channels")

    channels = Channel.objects.filter(user=request.user).order_by("created")
    num_checks = Check.objects.filter(user=request.user).count()

    ctx = {
        "page": "channels",
        "channels": channels,
        "num_checks": num_checks,
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None,
    }
    return render(request, "front/channels.html", ctx)


def do_add_channel(request, data):
    form = AddChannelForm(data)
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
def add_channel(request):
    assert request.method == "POST"
    return do_add_channel(request, request.POST)

@login_required
@uuid_or_400
def channel_checks(request, code):
    channel = get_object_or_404(Channel, code=code)
    if channel.user_id != request.user.id:
        return HttpResponseForbidden()

    assigned = set(channel.checks.values_list('code', flat=True).distinct())
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


@login_required
def add_email(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_email.html", ctx)


@login_required
def add_webhook(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_webhook.html", ctx)


@login_required
def add_pd(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_pd.html", ctx)


@login_required
def add_slack(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_slack.html", ctx)


@login_required
def add_hipchat(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_hipchat.html", ctx)


@login_required
def add_pushover(request):
    if settings.PUSHOVER_API_TOKEN is None or settings.PUSHOVER_SUBSCRIPTION_URL is None:
        return HttpResponseForbidden()

    if request.method == "POST":
        # Initiate the subscription
        nonce = get_random_string()
        request.session["po_nonce"] = nonce

        failure_url = settings.SITE_ROOT + reverse("hc-channels")
        success_url = settings.SITE_ROOT + reverse("hc-add-pushover") + "?" + urlencode({
            "nonce": nonce,
            "prio": request.POST.get("po_priority", "0"),
        })
        subscription_url = settings.PUSHOVER_SUBSCRIPTION_URL + "?" + urlencode({
            "success": success_url,
            "failure": failure_url,
        })

        return redirect(subscription_url)

    # Handle successful subscriptions
    if "pushover_user_key" in request.GET:
        if "nonce" not in request.GET or "prio" not in request.GET:
            return HttpResponseBadRequest()

        # Validate nonce
        if request.GET["nonce"] != request.session.get("po_nonce"):
            return HttpResponseForbidden()

        # Validate priority
        if request.GET["prio"] not in ("-2", "-1", "0", "1", "2"):
            return HttpResponseBadRequest()

        # All looks well--
        del request.session["po_nonce"]

        if request.GET.get("pushover_unsubscribed") == "1":
            # Unsubscription: delete all Pushover channels for this user
            Channel.objects.filter(user=request.user, kind="po").delete()
            return redirect("hc-channels")
        else:
            # Subscription
            user_key = request.GET["pushover_user_key"]
            priority = int(request.GET["prio"])

            return do_add_channel(request, {
                "kind": "po",
                "value": "%s|%d" % (user_key, priority),
            })

    # Show Integration Settings form
    ctx = {
        "page": "channels",
        "po_retry_delay": td(seconds=settings.PUSHOVER_EMERGENCY_RETRY_DELAY),
        "po_expiration": td(seconds=settings.PUSHOVER_EMERGENCY_EXPIRATION),
    }
    return render(request, "integrations/add_pushover.html", ctx)


def privacy(request):
    return render(request, "front/privacy.html", {})
