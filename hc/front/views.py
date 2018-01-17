from datetime import datetime, timedelta as td
import json

from croniter import croniter
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db.models import Count
from django.http import (Http404, HttpResponse, HttpResponseBadRequest,
                         HttpResponseForbidden)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.six.moves.urllib.parse import urlencode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from hc.api.decorators import uuid_or_400
from hc.api.models import (DEFAULT_GRACE, DEFAULT_TIMEOUT, Channel, Check,
                           Ping, Notification)
from hc.api.transports import Telegram
from hc.front.forms import (AddWebhookForm, NameTagsForm,
                            TimeoutForm, AddUrlForm, AddEmailForm,
                            AddOpsGenieForm, CronForm, AddSmsForm)
from hc.front.schemas import telegram_callback
from hc.lib import jsonschema
from pytz import all_timezones
from pytz.exceptions import UnknownTimeZoneError
import requests


VALID_SORT_VALUES = ("name", "-name", "last_ping", "-last_ping", "created")


@login_required
def my_checks(request):
    if request.GET.get("sort") in VALID_SORT_VALUES:
        request.profile.sort = request.GET["sort"]
        request.profile.save()

    checks = list(Check.objects.filter(user=request.team.user))

    tags, down_tags, grace_tags = set(), set(), set()
    for check in checks:
        status = check.get_status()
        for tag in check.tags_list():
            tags.add(tag)

            if status == "down":
                down_tags.add(tag)
            elif check.in_grace_period():
                grace_tags.add(tag)

    can_add_more = len(checks) < request.team.check_limit

    ctx = {
        "page": "checks",
        "checks": checks,
        "now": timezone.now(),
        "tags": sorted(tags, key=lambda s: s.lower()),
        "down_tags": down_tags,
        "grace_tags": grace_tags,
        "ping_endpoint": settings.PING_ENDPOINT,
        "timezones": all_timezones,
        "can_add_more": can_add_more,
        "sort": request.profile.sort
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
        "enable_pushbullet": settings.PUSHBULLET_CLIENT_ID is not None,
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None,
        "enable_discord": settings.DISCORD_CLIENT_ID is not None,
        "enable_telegram": settings.TELEGRAM_TOKEN is not None,
        "enable_sms": settings.TWILIO_AUTH is not None,
        "enable_pd": settings.PD_VENDOR_KEY is not None,
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
@uuid_or_400
def update_name(request, code):
    check = get_object_or_404(Check, code=code)
    if check.user_id != request.team.user.id:
        return HttpResponseForbidden()

    form = NameTagsForm(request.POST)
    if form.is_valid():
        check.name = form.cleaned_data["name"]
        check.tags = form.cleaned_data["tags"]
        check.save()

    return redirect("hc-checks")


@require_POST
@login_required
@uuid_or_400
def update_timeout(request, code):
    check = get_object_or_404(Check, code=code)
    if check.user != request.team.user:
        return HttpResponseForbidden()

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
                aware = timezone.make_aware(naive)
                ctx["dates"].append((naive, aware))
    except UnknownTimeZoneError:
        ctx["bad_tz"] = True
    except:
        ctx["bad_schedule"] = True

    return render(request, "front/cron_preview.html", ctx)


@require_POST
def last_ping(request, code):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    check = get_object_or_404(Check, code=code)
    if check.user_id != request.team.user.id:
        return HttpResponseForbidden()

    ping = Ping.objects.filter(owner=check).latest("created")

    ctx = {
        "check": check,
        "ping": ping
    }

    return render(request, "front/last_ping.html", ctx)


@require_POST
@login_required
@uuid_or_400
def pause(request, code):
    check = get_object_or_404(Check, code=code)
    if check.user_id != request.team.user.id:
        return HttpResponseForbidden()

    check.status = "paused"
    check.save()

    return redirect("hc-checks")


@require_POST
@login_required
@uuid_or_400
def remove_check(request, code):
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
        "use_payments": settings.USE_PAYMENTS
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


@uuid_or_400
def unsubscribe_email(request, code, token):
    channel = get_object_or_404(Channel, code=code)
    if channel.make_token() != token:
        return render(request, "bad_link.html")

    if channel.kind != "email":
        return HttpResponseBadRequest()

    channel.delete()
    return render(request, "front/unsubscribe_success.html")


@require_POST
@login_required
@uuid_or_400
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

    if state and request.user.is_authenticated():
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

    if settings.SLACK_CLIENT_ID:
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


@csrf_exempt
@require_POST
def telegram_bot(request):
    try:
        doc = json.loads(request.body.decode("utf-8"))
        jsonschema.validate(doc, telegram_callback)
    except ValueError:
        return HttpResponseBadRequest()
    except jsonschema.ValidationError:
        return HttpResponseBadRequest()

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
            channel.value = form.cleaned_data["value"]
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
