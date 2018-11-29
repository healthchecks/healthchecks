from datetime import datetime, timedelta as td
import json
from urllib.parse import urlencode

from croniter import croniter
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db.models import Count
from django.http import (Http404, HttpResponse, HttpResponseBadRequest,
                         HttpResponseForbidden, JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from hc.api.models import (DEFAULT_GRACE, DEFAULT_TIMEOUT, Channel, Check,
                           Ping, Notification)
from hc.api.transports import Telegram
from hc.front.forms import (AddWebhookForm, NameTagsForm,
                            TimeoutForm, AddUrlForm, AddEmailForm,
                            AddOpsGenieForm, CronForm, AddSmsForm,
                            ChannelNameForm)
from hc.front.schemas import telegram_callback
from hc.front.templatetags.hc_extras import (num_down_title, down_title,
                                             sortchecks)
from hc.lib import jsonschema
from pytz import all_timezones
from pytz.exceptions import UnknownTimeZoneError
import requests


VALID_SORT_VALUES = ("name", "-name", "last_ping", "-last_ping", "created")
STATUS_TEXT_TMPL = get_template("front/log_status_text.html")
LAST_PING_TMPL = get_template("front/last_ping_cell.html")
EVENTS_TMPL = get_template("front/details_events.html")


def _tags_statuses(checks):
    tags, down, grace, num_down = {}, {}, {}, 0
    for check in checks:
        status = check.get_status()

        if status == "down":
            num_down += 1
            for tag in check.tags_list():
                down[tag] = "down"
        elif status == "grace":
            for tag in check.tags_list():
                grace[tag] = "grace"
        else:
            for tag in check.tags_list():
                tags[tag] = "up"

    tags.update(grace)
    tags.update(down)
    return tags, num_down


def _get_check_for_user(request, code):
    """ Return specified check if current user has access to it. """

    if not request.user.is_authenticated:
        raise Http404("not found")

    if request.user.is_superuser:
        q = Check.objects
    else:
        q = request.profile.checks_from_all_teams()

    try:
        return q.get(code=code)
    except Check.DoesNotExist:
        raise Http404("not found")


@login_required
def my_checks(request):
    if request.GET.get("sort") in VALID_SORT_VALUES:
        request.profile.sort = request.GET["sort"]
        request.profile.save()

    checks = list(Check.objects.filter(user=request.team.user).prefetch_related("channel_set"))
    sortchecks(checks, request.profile.sort)

    tags_statuses, num_down = _tags_statuses(checks)
    pairs = list(tags_statuses.items())
    pairs.sort(key=lambda pair: pair[0].lower())

    channels = Channel.objects.filter(user=request.team.user)
    channels = list(channels.order_by("created"))

    hidden_checks = set()
    # Hide checks that don't match selected tags:
    selected_tags = set(request.GET.getlist("tag", []))
    if selected_tags:
        for check in checks:
            if not selected_tags.issubset(check.tags_list()):
                hidden_checks.add(check)

    # Hide checks that don't match the search string:
    search = request.GET.get("search", "")
    if search:
        for check in checks:
            search_key = "%s\n%s" % (check.name.lower(), check.code)
            if search not in search_key:
                hidden_checks.add(check)

    ctx = {
        "page": "checks",
        "checks": checks,
        "channels": channels,
        "num_down": num_down,
        "now": timezone.now(),
        "tags": pairs,
        "ping_endpoint": settings.PING_ENDPOINT,
        "timezones": all_timezones,
        "num_available": request.team.check_limit - len(checks),
        "sort": request.profile.sort,
        "selected_tags": selected_tags,
        "show_search": True,
        "search": search,
        "hidden_checks": hidden_checks
    }

    return render(request, "front/my_checks.html", ctx)


@login_required
def status(request):
    checks = list(Check.objects.filter(user_id=request.team.user_id))

    details = []
    for check in checks:
        ctx = {"check": check}
        details.append({
            "code": str(check.code),
            "status": check.get_status(),
            "last_ping": LAST_PING_TMPL.render(ctx)
        })

    tags_statuses, num_down = _tags_statuses(checks)
    return JsonResponse({
        "details": details,
        "tags": tags_statuses,
        "title": num_down_title(num_down)
    })


@login_required
@require_POST
def switch_channel(request, code, channel_code):
    check = _get_check_for_user(request, code)

    channel = get_object_or_404(Channel, code=channel_code)
    if channel.user_id != check.user_id:
        return HttpResponseBadRequest()

    if request.POST.get("state") == "on":
        channel.checks.add(check)
    else:
        channel.checks.remove(check)

    return HttpResponse()


def index(request):
    if request.user.is_authenticated:
        return redirect("hc-checks")

    check = Check()

    ctx = {
        "page": "welcome",
        "check": check,
        "ping_url": check.url(),
        "enable_pushbullet": settings.PUSHBULLET_CLIENT_ID is not None,
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None,
        "enable_discord": settings.DISCORD_CLIENT_ID is not None,
        "enable_telegram": settings.TELEGRAM_TOKEN is not None,
        "enable_sms": settings.TWILIO_AUTH is not None,
        "enable_pd": settings.PD_VENDOR_KEY is not None,
        "enable_trello": settings.TRELLO_APP_KEY is not None,
        "registration_open": settings.REGISTRATION_OPEN
    }

    return render(request, "front/welcome.html", ctx)


def docs(request):
    ctx = {
        "page": "docs",
        "section": "home",
        "ping_endpoint": settings.PING_ENDPOINT,
        "ping_email": "your-uuid-here@%s" % settings.PING_EMAIL_DOMAIN,
        "ping_url": settings.PING_ENDPOINT + "your-uuid-here"
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


def docs_cron(request):
    ctx = {"page": "docs", "section": "cron"}
    return render(request, "front/docs_cron.html", ctx)


def docs_resources(request):
    ctx = {"page": "docs", "section": "resources"}
    return render(request, "front/docs_resources.html", ctx)


@require_POST
@login_required
def add_check(request):
    num_checks = Check.objects.filter(user=request.team.user).count()
    if num_checks >= request.team.check_limit:
        return HttpResponseBadRequest()

    check = Check(user=request.team.user)
    check.save()

    check.assign_all_channels()

    return redirect("hc-checks")


@require_POST
@login_required
def update_name(request, code):
    check = _get_check_for_user(request, code)
    form = NameTagsForm(request.POST)
    if form.is_valid():
        check.name = form.cleaned_data["name"]
        check.tags = form.cleaned_data["tags"]
        check.desc = form.cleaned_data["desc"]
        check.save()

    if "/details/" in request.META.get("HTTP_REFERER", ""):
        return redirect("hc-details", code)

    return redirect("hc-checks")


@require_POST
@login_required
def update_timeout(request, code):
    check = _get_check_for_user(request, code)

    kind = request.POST.get("kind")
    if kind == "simple":
        form = TimeoutForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "simple"
        check.timeout = form.cleaned_data["timeout"]
        check.grace = form.cleaned_data["grace"]
    elif kind == "cron":
        form = CronForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "cron"
        check.schedule = form.cleaned_data["schedule"]
        check.tz = form.cleaned_data["tz"]
        check.grace = td(minutes=form.cleaned_data["grace"])

    if check.last_ping:
        check.alert_after = check.get_alert_after()

    check.save()

    if "/details/" in request.META.get("HTTP_REFERER", ""):
        return redirect("hc-details", code)

    return redirect("hc-checks")


@require_POST
def cron_preview(request):
    schedule = request.POST.get("schedule")
    tz = request.POST.get("tz")
    ctx = {"tz": tz, "dates": []}
    try:
        with timezone.override(tz):
            now_naive = timezone.make_naive(timezone.now())
            it = croniter(schedule, now_naive)
            for i in range(0, 6):
                naive = it.get_next(datetime)
                aware = timezone.make_aware(naive, is_dst=True)
                ctx["dates"].append((naive, aware))
    except UnknownTimeZoneError:
        ctx["bad_tz"] = True
    except:
        ctx["bad_schedule"] = True

    return render(request, "front/cron_preview.html", ctx)


def ping_details(request, code, n=None):
    check = _get_check_for_user(request, code)
    q = Ping.objects.filter(owner=check)
    if n:
        q = q.filter(n=n)

    ping = q.latest("created")

    ctx = {
        "check": check,
        "ping": ping
    }

    return render(request, "front/ping_details.html", ctx)


@require_POST
@login_required
def pause(request, code):
    check = _get_check_for_user(request, code)

    check.status = "paused"
    check.save()

    if "/details/" in request.META.get("HTTP_REFERER", ""):
        return redirect("hc-details", code)

    return redirect("hc-checks")


@require_POST
@login_required
def remove_check(request, code):
    check = _get_check_for_user(request, code)
    check.delete()
    return redirect("hc-checks")


def _get_events(check, limit):
    pings = Ping.objects.filter(owner=check).order_by("-id")[:limit]
    pings = list(pings)

    alerts = []
    if len(pings):
        cutoff = pings[-1].created
        alerts = Notification.objects \
            .select_related("channel") \
            .filter(owner=check, check_status="down", created__gt=cutoff)

    events = pings + list(alerts)
    events.sort(key=lambda el: el.created, reverse=True)
    return events


@login_required
def log(request, code):
    check = _get_check_for_user(request, code)

    limit = check.user.profile.ping_log_limit
    ctx = {
        "check": check,
        "events": _get_events(check, limit),
        "limit": limit,
        "show_limit_notice": check.n_pings > limit and settings.USE_PAYMENTS
    }

    return render(request, "front/log.html", ctx)


@login_required
def details(request, code):
    check = _get_check_for_user(request, code)

    channels = Channel.objects.filter(user=check.user)
    channels = list(channels.order_by("created"))

    ctx = {
        "page": "details",
        "check": check,
        "channels": channels,
        "timezones": all_timezones
    }

    return render(request, "front/details.html", ctx)


@login_required
def status_single(request, code):
    check = _get_check_for_user(request, code)

    status = check.get_status()
    events = _get_events(check, 20)
    updated = "1"
    if len(events):
        updated = events[0].created.strftime("%s.%f")

    doc = {
        "status": status,
        "status_text": STATUS_TEXT_TMPL.render({"check": check}),
        "title": down_title(check),
        "updated": updated
    }

    if updated != request.GET.get("u"):
        doc["events"] = EVENTS_TMPL.render({"check": check, "events": events})

    return JsonResponse(doc)


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

        channel.checks.set(new_checks)
        return redirect("hc-channels")

    channels = Channel.objects.filter(user=request.team.user)
    channels = channels.order_by("created")
    channels = channels.annotate(n_checks=Count("checks"))

    num_checks = Check.objects.filter(user=request.team.user).count()

    ctx = {
        "page": "channels",
        "profile": request.team,
        "channels": channels,
        "num_checks": num_checks,
        "enable_pushbullet": settings.PUSHBULLET_CLIENT_ID is not None,
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None,
        "enable_discord": settings.DISCORD_CLIENT_ID is not None,
        "enable_telegram": settings.TELEGRAM_TOKEN is not None,
        "enable_sms": settings.TWILIO_AUTH is not None,
        "enable_pd": settings.PD_VENDOR_KEY is not None,
        "enable_zendesk": settings.ZENDESK_CLIENT_ID is not None,
        "enable_trello": settings.TRELLO_APP_KEY is not None,
        "use_payments": settings.USE_PAYMENTS
    }

    return render(request, "front/channels.html", ctx)


@login_required
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


@require_POST
@login_required
def update_channel_name(request, code):
    channel = get_object_or_404(Channel, code=code)
    if channel.user_id != request.team.user.id:
        return HttpResponseForbidden()

    form = ChannelNameForm(request.POST)
    if form.is_valid():
        channel.name = form.cleaned_data["name"]
        channel.save()

    return redirect("hc-channels")


def verify_email(request, code, token):
    channel = get_object_or_404(Channel, code=code)
    if channel.make_token() == token:
        channel.email_verified = True
        channel.save()
        return render(request, "front/verify_email_success.html")

    return render(request, "bad_link.html")


def unsubscribe_email(request, code, token):
    channel = get_object_or_404(Channel, code=code)
    if channel.make_token() != token:
        return render(request, "bad_link.html")

    if channel.kind != "email":
        return HttpResponseBadRequest()

    # Some email servers open links in emails to check for malicious content.
    # To work around this, we serve a form that auto-submits with JS.
    if "ask" in request.GET and request.method != "POST":
        return render(request, "accounts/unsubscribe_submit.html")

    channel.delete()
    return render(request, "front/unsubscribe_success.html")


@require_POST
@login_required
def remove_channel(request, code):
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

    ctx = {
        "page": "channels",
        "form": form,
        "now": timezone.now().replace(microsecond=0).isoformat()
    }
    return render(request, "integrations/add_webhook.html", ctx)


def _prepare_state(request, session_key):
    state = get_random_string()
    request.session[session_key] = state
    return state


def _get_validated_code(request, session_key, key="code"):
    if session_key not in request.session:
        return None

    session_state = request.session.pop(session_key)
    request_state = request.GET.get("state")
    if session_state is None or session_state != request_state:
        return None

    return request.GET.get(key)


def add_pd(request, state=None):
    if settings.PD_VENDOR_KEY is None:
        raise Http404("pagerduty integration is not available")

    if state and request.user.is_authenticated:
        if "pd" not in request.session:
            return HttpResponseBadRequest()

        session_state = request.session.pop("pd")
        if session_state != state:
            return HttpResponseBadRequest()

        if request.GET.get("error") == "cancelled":
            messages.warning(request, "PagerDuty setup was cancelled")
            return redirect("hc-channels")

        channel = Channel()
        channel.user = request.team.user
        channel.kind = "pd"
        channel.value = json.dumps({
            "service_key": request.GET.get("service_key"),
            "account": request.GET.get("account")
        })
        channel.save()
        channel.assign_all_checks()
        messages.success(request, "The PagerDuty integration has been added!")
        return redirect("hc-channels")

    state = _prepare_state(request, "pd")
    callback = settings.SITE_ROOT + reverse("hc-add-pd-state", args=[state])
    connect_url = "https://connect.pagerduty.com/connect?" + urlencode({
        "vendor": settings.PD_VENDOR_KEY,
        "callback": callback
    })

    ctx = {"page": "channels", "connect_url": connect_url}
    return render(request, "integrations/add_pd.html", ctx)


@login_required
def add_pagertree(request):
    if request.method == "POST":
        form = AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="pagertree")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels")
    else:
        form = AddUrlForm()

    ctx = {"page": "channels", "form": form}
    return render(request, "integrations/add_pagertree.html", ctx)


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

    if settings.SLACK_CLIENT_ID and request.user.is_authenticated:
        ctx["state"] = _prepare_state(request, "slack")

    return render(request, "integrations/add_slack.html", ctx)


@login_required
def add_slack_btn(request):
    code = _get_validated_code(request, "slack")
    if code is None:
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
    if "installable_url" in request.GET:
        url = request.GET["installable_url"]
        assert url.startswith("https://api.hipchat.com")
        response = requests.get(url)
        if "oauthId" not in response.json():
            messages.warning(request, "Something went wrong!")
            return redirect("hc-channels")

        channel = Channel(kind="hipchat")
        channel.user = request.team.user
        channel.value = response.text
        channel.save()

        channel.refresh_hipchat_access_token()
        channel.assign_all_checks()
        messages.success(request, "The HipChat integration has been added!")
        return redirect("hc-channels")

    install_url = "https://www.hipchat.com/addons/install?" + urlencode({
        "url": settings.SITE_ROOT + reverse("hc-hipchat-capabilities")
    })

    ctx = {
        "page": "channels",
        "install_url": install_url
    }
    return render(request, "integrations/add_hipchat.html", ctx)


def hipchat_capabilities(request):
    return render(request, "integrations/hipchat_capabilities.json", {},
                  content_type="application/json")


@login_required
def add_pushbullet(request):
    if settings.PUSHBULLET_CLIENT_ID is None:
        raise Http404("pushbullet integration is not available")

    if "code" in request.GET:
        code = _get_validated_code(request, "pushbullet")
        if code is None:
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
        "response_type": "code",
        "state": _prepare_state(request, "pushbullet")
    })

    ctx = {
        "page": "channels",
        "authorize_url": authorize_url
    }
    return render(request, "integrations/add_pushbullet.html", ctx)


@login_required
def add_discord(request):
    if settings.DISCORD_CLIENT_ID is None:
        raise Http404("discord integration is not available")

    redirect_uri = settings.SITE_ROOT + reverse("hc-add-discord")
    if "code" in request.GET:
        code = _get_validated_code(request, "discord")
        if code is None:
            return HttpResponseBadRequest()

        result = requests.post("https://discordapp.com/api/oauth2/token", {
            "client_id": settings.DISCORD_CLIENT_ID,
            "client_secret": settings.DISCORD_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        })

        doc = result.json()
        if "access_token" in doc:
            channel = Channel(kind="discord")
            channel.user = request.team.user
            channel.value = result.text
            channel.save()
            channel.assign_all_checks()
            messages.success(request,
                             "The Discord integration has been added!")
        else:
            messages.warning(request, "Something went wrong")

        return redirect("hc-channels")

    auth_url = "https://discordapp.com/api/oauth2/authorize?" + urlencode({
        "client_id": settings.DISCORD_CLIENT_ID,
        "scope": "webhook.incoming",
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": _prepare_state(request, "discord")
    })

    ctx = {
        "page": "channels",
        "authorize_url": auth_url
    }

    return render(request, "integrations/add_discord.html", ctx)


def add_pushover(request):
    if settings.PUSHOVER_API_TOKEN is None or settings.PUSHOVER_SUBSCRIPTION_URL is None:
        raise Http404("pushover integration is not available")

    if not request.user.is_authenticated:
        ctx = {"page": "channels"}
        return render(request, "integrations/add_pushover.html", ctx)

    if request.method == "POST":
        # Initiate the subscription
        state = _prepare_state(request, "pushover")

        failure_url = settings.SITE_ROOT + reverse("hc-channels")
        success_url = settings.SITE_ROOT + reverse("hc-add-pushover") + "?" + urlencode({
            "state": state,
            "prio": request.POST.get("po_priority", "0"),
            "prio_up": request.POST.get("po_priority_up", "0")
        })
        subscription_url = settings.PUSHOVER_SUBSCRIPTION_URL + "?" + urlencode({
            "success": success_url,
            "failure": failure_url,
        })

        return redirect(subscription_url)

    # Handle successful subscriptions
    if "pushover_user_key" in request.GET:
        key = _get_validated_code(request, "pushover", "pushover_user_key")
        if key is None:
            return HttpResponseBadRequest()

        # Validate priority
        prio = request.GET.get("prio")
        if prio not in ("-2", "-1", "0", "1", "2"):
            return HttpResponseBadRequest()

        prio_up = request.GET.get("prio_up")
        if prio_up not in ("-2", "-1", "0", "1", "2"):
            return HttpResponseBadRequest()

        if request.GET.get("pushover_unsubscribed") == "1":
            # Unsubscription: delete all Pushover channels for this user
            Channel.objects.filter(user=request.user, kind="po").delete()
            return redirect("hc-channels")

        # Subscription
        channel = Channel(user=request.team.user, kind="po")
        channel.value = "%s|%s|%s" % (key, prio, prio_up)
        channel.save()
        channel.assign_all_checks()

        messages.success(request, "The Pushover integration has been added!")
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


@csrf_exempt
@require_POST
def telegram_bot(request):
    try:
        doc = json.loads(request.body.decode())
        jsonschema.validate(doc, telegram_callback)
    except ValueError:
        return HttpResponseBadRequest()
    except jsonschema.ValidationError:
        # We don't recognize the message format, but don't want Telegram
        # retrying this over and over again, so respond with 200 OK
        return HttpResponse()

    if "/start" not in doc["message"]["text"]:
        return HttpResponse()

    chat = doc["message"]["chat"]
    name = max(chat.get("title", ""), chat.get("username", ""))

    invite = render_to_string("integrations/telegram_invite.html", {
        "qs": signing.dumps((chat["id"], chat["type"], name))
    })

    Telegram.send(chat["id"], invite)
    return HttpResponse()


@login_required
def add_telegram(request):
    chat_id, chat_type, chat_name = None, None, None
    qs = request.META["QUERY_STRING"]
    if qs:
        chat_id, chat_type, chat_name = signing.loads(qs, max_age=600)

    if request.method == "POST":
        channel = Channel(user=request.team.user, kind="telegram")
        channel.value = json.dumps({
            "id": chat_id,
            "type": chat_type,
            "name": chat_name
        })
        channel.save()

        channel.assign_all_checks()
        messages.success(request, "The Telegram integration has been added!")
        return redirect("hc-channels")

    ctx = {
        "chat_id": chat_id,
        "chat_type": chat_type,
        "chat_name": chat_name,
        "bot_name": settings.TELEGRAM_BOT_NAME
    }

    return render(request, "integrations/add_telegram.html", ctx)


@login_required
def add_sms(request):
    if settings.TWILIO_AUTH is None:
        raise Http404("sms integration is not available")

    if request.method == "POST":
        form = AddSmsForm(request.POST)
        if form.is_valid():
            channel = Channel(user=request.team.user, kind="sms")
            channel.name = form.cleaned_data["label"]
            channel.value = json.dumps({
                "value": form.cleaned_data["value"]
            })
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels")
    else:
        form = AddSmsForm()

    ctx = {
        "page": "channels",
        "form": form,
        "profile": request.team
    }
    return render(request, "integrations/add_sms.html", ctx)


@login_required
def add_zendesk(request):
    if settings.ZENDESK_CLIENT_ID is None:
        raise Http404("zendesk integration is not available")

    if request.method == "POST":
        domain = request.POST.get("subdomain")
        request.session["subdomain"] = domain
        redirect_uri = settings.SITE_ROOT + reverse("hc-add-zendesk")
        auth_url = "https://%s.zendesk.com/oauth/authorizations/new?" % domain
        auth_url += urlencode({
            "client_id": settings.ZENDESK_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "requests:read requests:write",
            "state": _prepare_state(request, "zendesk")
        })

        return redirect(auth_url)

    if "code" in request.GET:
        code = _get_validated_code(request, "zendesk")
        if code is None:
            return HttpResponseBadRequest()

        domain = request.session.pop("subdomain")
        url = "https://%s.zendesk.com/oauth/tokens" % domain

        redirect_uri = settings.SITE_ROOT + reverse("hc-add-zendesk")
        result = requests.post(url, {
            "client_id": settings.ZENDESK_CLIENT_ID,
            "client_secret": settings.ZENDESK_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "scope": "read"
        })

        doc = result.json()
        if "access_token" in doc:
            doc["subdomain"] = domain

            channel = Channel(kind="zendesk")
            channel.user = request.team.user
            channel.value = json.dumps(doc)
            channel.save()
            channel.assign_all_checks()
            messages.success(request,
                             "The Zendesk integration has been added!")
        else:
            messages.warning(request, "Something went wrong")

        return redirect("hc-channels")

    ctx = {"page": "channels"}
    return render(request, "integrations/add_zendesk.html", ctx)


@login_required
def add_trello(request):
    if settings.TRELLO_APP_KEY is None:
        raise Http404("trello integration is not available")

    if request.method == "POST":
        channel = Channel(user=request.team.user, kind="trello")
        channel.value = request.POST["settings"]
        channel.save()

        channel.assign_all_checks()
        return redirect("hc-channels")

    authorize_url = "https://trello.com/1/authorize?" + urlencode({
        "expiration": "never",
        "name": settings.SITE_NAME,
        "scope": "read,write",
        "response_type": "token",
        "key": settings.TRELLO_APP_KEY,
        "return_url": settings.SITE_ROOT + reverse("hc-add-trello")
    })

    ctx = {
        "page": "channels",
        "authorize_url": authorize_url
    }

    return render(request, "integrations/add_trello.html", ctx)


@login_required
@require_POST
def trello_settings(request):
    token = request.POST.get("token")

    url = "https://api.trello.com/1/members/me/boards?" + urlencode({
        "key": settings.TRELLO_APP_KEY,
        "token": token,
        "fields": "id,name",
        "lists": "open",
        "list_fields": "id,name"
    })

    r = requests.get(url)
    ctx = {
        "token": token,
        "data": r.json()
    }
    return render(request, "integrations/trello_settings.html", ctx)
