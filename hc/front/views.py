from collections import Counter
from croniter import croniter
from datetime import datetime, timedelta as td
from itertools import tee

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.six.moves.urllib.parse import urlencode
from hc.api.decorators import uuid_or_400
from hc.api.models import (DEFAULT_GRACE, DEFAULT_TIMEOUT, Channel, Check,
                           Ping, Notification)
from hc.front.forms import (AddWebhookForm, NameTagsForm,
                            TimeoutForm, AddUrlForm, AddPdForm, AddEmailForm,
                            AddOpsGenieForm, CronForm)
from pytz import all_timezones


# from itertools recipes:
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


@login_required
def my_checks(request):
    q = Check.objects.filter(user=request.team.user).order_by("created")
    checks = list(q)

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
            elif check.in_grace_period():
                grace_tags.add(tag)

    ctx = {
        "page": "checks",
        "checks": checks,
        "now": timezone.now(),
        "tags": counter.most_common(),
        "down_tags": down_tags,
        "grace_tags": grace_tags,
        "ping_endpoint": settings.PING_ENDPOINT,
        "timezones": all_timezones
    }

    return render(request, "front/my_checks.html", ctx)


def _welcome_check(request):
    check = None
    if "welcome_code" in request.session:
        code = request.session["welcome_code"]
        check = Check.objects.filter(code=code).first()

    if check is None:
        check = Check()
        check.save()
        request.session["welcome_code"] = str(check.code)

    return check


def index(request):
    if request.user.is_authenticated:
        return redirect("hc-checks")

    check = _welcome_check(request)

    ctx = {
        "page": "welcome",
        "check": check,
        "ping_url": check.url(),
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None
    }

    return render(request, "front/welcome.html", ctx)


def docs(request):
    check = _welcome_check(request)

    ctx = {
        "page": "docs",
        "section": "home",
        "ping_endpoint": settings.PING_ENDPOINT,
        "check": check,
        "ping_url": check.url()
    }

    return render(request, "front/docs.html", ctx)


def docs_api(request):
    ctx = {
        "page": "docs",
        "section": "api",
        "SITE_ROOT": settings.SITE_ROOT,
        "PING_ENDPOINT": settings.PING_ENDPOINT,
        "default_timeout": int(DEFAULT_TIMEOUT.total_seconds()),
        "default_grace": int(DEFAULT_GRACE.total_seconds())
    }

    return render(request, "front/docs_api.html", ctx)


def about(request):
    return render(request, "front/about.html", {"page": "about"})


@login_required
def add_check(request):
    if request.method != "POST":
        return HttpResponseBadRequest()

    check = Check(user=request.team.user)
    check.save()

    check.assign_all_channels()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def update_name(request, code):
    if request.method != "POST":
        return HttpResponseBadRequest()

    check = get_object_or_404(Check, code=code)
    if check.user_id != request.team.user.id:
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
    if request.method != "POST":
        return HttpResponseBadRequest()

    check = get_object_or_404(Check, code=code)
    if check.user != request.team.user:
        return HttpResponseForbidden()

    kind = request.POST.get("kind")
    if kind == "simple":
        form = TimeoutForm(request.POST)
        if not form.is_valid():
            return redirect("hc-checks")

        check.kind = "simple"
        check.timeout = td(seconds=form.cleaned_data["timeout"])
        check.grace = td(seconds=form.cleaned_data["grace"])
    elif kind == "cron":
        form = CronForm(request.POST)
        if not form.is_valid():
            return redirect("hc-checks")

        check.kind = "cron"
        check.schedule = form.cleaned_data["schedule"]
        check.tz = form.cleaned_data["tz"]
        check.grace = td(minutes=form.cleaned_data["grace"])

    if check.last_ping:
        check.alert_after = check.get_alert_after()

    check.save()
    return redirect("hc-checks")


@csrf_exempt
def cron_preview(request):
    schedule = request.POST.get("schedule")
    tz = request.POST.get("tz")

    ctx = {
        "tz": tz,
        "dates": []
    }

    try:
        with timezone.override(tz):
            now_naive = timezone.make_naive(timezone.now())
            it = croniter(schedule, now_naive)
            for i in range(0, 6):
                date_naive = it.get_next(datetime)
                ctx["dates"].append(timezone.make_aware(date_naive))
    except:
        ctx["error"] = True

    return render(request, "front/cron_preview.html", ctx)


@login_required
@uuid_or_400
def pause(request, code):
    if request.method != "POST":
        return HttpResponseBadRequest()

    check = get_object_or_404(Check, code=code)
    if check.user_id != request.team.user.id:
        return HttpResponseForbidden()

    check.status = "paused"
    check.save()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def remove_check(request, code):
    if request.method != "POST":
        return HttpResponseBadRequest()

    check = get_object_or_404(Check, code=code)
    if check.user != request.team.user:
        return HttpResponseForbidden()

    check.delete()

    return redirect("hc-checks")


@login_required
@uuid_or_400
def log(request, code):
    check = get_object_or_404(Check, code=code)
    if check.user != request.team.user:
        return HttpResponseForbidden()

    limit = request.team.ping_log_limit
    pings = Ping.objects.filter(owner=check).order_by("-id")[:limit + 1]
    pings = list(pings)

    num_pings = len(pings)
    pings = pings[:limit]

    alerts = []
    if len(pings):
        cutoff = pings[-1].created
        alerts = Notification.objects \
            .select_related("channel") \
            .filter(owner=check, check_status="down", created__gt=cutoff)

    events = pings + list(alerts)
    events.sort(key=lambda el: el.created, reverse=True)

    ctx = {
        "check": check,
        "events": events,
        "num_pings": min(num_pings, limit),
        "limit": limit,
        "show_limit_notice": num_pings > limit and settings.USE_PAYMENTS
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
        if channel.user_id != request.team.user.id:
            return HttpResponseForbidden()

        new_checks = []
        for key in request.POST:
            if key.startswith("check-"):
                code = key[6:]
                try:
                    check = Check.objects.get(code=code)
                except Check.DoesNotExist:
                    return HttpResponseBadRequest()
                if check.user_id != request.team.user.id:
                    return HttpResponseForbidden()
                new_checks.append(check)

        channel.checks = new_checks
        return redirect("hc-channels")

    channels = Channel.objects.filter(user=request.team.user).order_by("created")
    channels = channels.annotate(n_checks=Count("checks"))

    num_checks = Check.objects.filter(user=request.team.user).count()

    ctx = {
        "page": "channels",
        "channels": channels,
        "num_checks": num_checks,
        "enable_pushbullet": settings.PUSHBULLET_CLIENT_ID is not None,
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None
    }
    return render(request, "front/channels.html", ctx)


@login_required
@uuid_or_400
def channel_checks(request, code):
    channel = get_object_or_404(Channel, code=code)
    if channel.user_id != request.team.user.id:
        return HttpResponseForbidden()

    assigned = set(channel.checks.values_list('code', flat=True).distinct())
    checks = Check.objects.filter(user=request.team.user).order_by("created")

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
    if request.method != "POST":
        return HttpResponseBadRequest()

    # user may refresh the page during POST and cause two deletion attempts
    channel = Channel.objects.filter(code=code).first()
    if channel:
        if channel.user != request.team.user:
            return HttpResponseForbidden()
        channel.delete()

    return redirect("hc-channels")


@login_required
def add_email(request):
    if request.method == "POST":
        form = AddEmailForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="email")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            channel.send_verify_link()
            return redirect("hc-channels")
    else:
        form = AddEmailForm()

    ctx = {"page": "channels", "form": form}
    return render(request, "integrations/add_email.html", ctx)


@login_required
def add_webhook(request):
    if request.method == "POST":
        form = AddWebhookForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="webhook")
            channel.value = form.get_value()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels")
    else:
        form = AddWebhookForm()

    ctx = {"page": "channels", "form": form}
    return render(request, "integrations/add_webhook.html", ctx)


@login_required
def add_pd(request):
    if request.method == "POST":
        form = AddPdForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="pd")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels")
    else:
        form = AddPdForm()

    ctx = {"page": "channels", "form": form}
    return render(request, "integrations/add_pd.html", ctx)


def add_slack(request):
    if not settings.SLACK_CLIENT_ID and not request.user.is_authenticated:
        return redirect("hc-login")

    if request.method == "POST":
        form = AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="slack")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels")
    else:
        form = AddUrlForm()

    ctx = {
        "page": "channels",
        "form": form,
        "slack_client_id": settings.SLACK_CLIENT_ID
    }

    return render(request, "integrations/add_slack.html", ctx)


@login_required
def add_slack_btn(request):
    code = request.GET.get("code", "")
    if len(code) < 8:
        return HttpResponseBadRequest()

    result = requests.post("https://slack.com/api/oauth.access", {
        "client_id": settings.SLACK_CLIENT_ID,
        "client_secret": settings.SLACK_CLIENT_SECRET,
        "code": code
    })

    doc = result.json()
    if doc.get("ok"):
        channel = Channel()
        channel.user = request.team.user
        channel.kind = "slack"
        channel.value = result.text
        channel.save()
        channel.assign_all_checks()
        messages.success(request, "The Slack integration has been added!")
    else:
        s = doc.get("error")
        messages.warning(request, "Error message from slack: %s" % s)

    return redirect("hc-channels")


@login_required
def add_hipchat(request):
    if request.method == "POST":
        form = AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="hipchat")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels")
    else:
        form = AddUrlForm()

    ctx = {"page": "channels", "form": form}
    return render(request, "integrations/add_hipchat.html", ctx)


@login_required
def add_pushbullet(request):
    if settings.PUSHBULLET_CLIENT_ID is None:
        raise Http404("pushbullet integration is not available")

    if "code" in request.GET:
        code = request.GET.get("code", "")
        if len(code) < 8:
            return HttpResponseBadRequest()

        result = requests.post("https://api.pushbullet.com/oauth2/token", {
            "client_id": settings.PUSHBULLET_CLIENT_ID,
            "client_secret": settings.PUSHBULLET_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        })

        doc = result.json()
        if "access_token" in doc:
            channel = Channel(kind="pushbullet")
            channel.user = request.team.user
            channel.value = doc["access_token"]
            channel.save()
            channel.assign_all_checks()
            messages.success(request,
                             "The Pushbullet integration has been added!")
        else:
            messages.warning(request, "Something went wrong")

        return redirect("hc-channels")

    redirect_uri = settings.SITE_ROOT + reverse("hc-add-pushbullet")
    authorize_url = "https://www.pushbullet.com/authorize?" + urlencode({
        "client_id": settings.PUSHBULLET_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code"
    })

    ctx = {
        "page": "channels",
        "authorize_url": authorize_url
    }
    return render(request, "integrations/add_pushbullet.html", ctx)


@login_required
def add_pushover(request):
    if settings.PUSHOVER_API_TOKEN is None or settings.PUSHOVER_SUBSCRIPTION_URL is None:
        raise Http404("pushover integration is not available")

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

            channel = Channel(user=request.team.user, kind="po")
            channel.value = "%s|%d" % (user_key, priority)
            channel.save()
            channel.assign_all_checks()
            return redirect("hc-channels")

    # Show Integration Settings form
    ctx = {
        "page": "channels",
        "po_retry_delay": td(seconds=settings.PUSHOVER_EMERGENCY_RETRY_DELAY),
        "po_expiration": td(seconds=settings.PUSHOVER_EMERGENCY_EXPIRATION),
    }
    return render(request, "integrations/add_pushover.html", ctx)


@login_required
def add_opsgenie(request):
    if request.method == "POST":
        form = AddOpsGenieForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="opsgenie")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels")
    else:
        form = AddUrlForm()

    ctx = {"page": "channels", "form": form}
    return render(request, "integrations/add_opsgenie.html", ctx)


@login_required
def add_victorops(request):
    if request.method == "POST":
        form = AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="victorops")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels")
    else:
        form = AddUrlForm()

    ctx = {"page": "channels", "form": form}
    return render(request, "integrations/add_victorops.html", ctx)


def privacy(request):
    return render(request, "front/privacy.html", {})


def terms(request):
    return render(request, "front/terms.html", {})
