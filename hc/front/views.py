from datetime import datetime, timedelta as td
import json
import os
from secrets import token_urlsafe
from urllib.parse import urlencode

from cron_descriptor import ExpressionDescriptor
from croniter import croniter
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from hc.accounts.models import Project, Member
from hc.api.models import (
    DEFAULT_GRACE,
    DEFAULT_TIMEOUT,
    MAX_DELTA,
    Channel,
    Check,
    Ping,
    Notification,
)
from hc.api.transports import Telegram
from hc.front.decorators import require_setting
from hc.front import forms
from hc.front.schemas import telegram_callback
from hc.front.templatetags.hc_extras import (
    num_down_title,
    down_title,
    sortchecks,
    site_hostname,
    site_scheme,
)
from hc.lib import jsonschema
from hc.lib.badges import get_badge_url
import pytz
from pytz.exceptions import UnknownTimeZoneError
import requests


VALID_SORT_VALUES = ("name", "-name", "last_ping", "-last_ping", "created")
STATUS_TEXT_TMPL = get_template("front/log_status_text.html")
LAST_PING_TMPL = get_template("front/last_ping_cell.html")
EVENTS_TMPL = get_template("front/details_events.html")
DOWNTIMES_TMPL = get_template("front/details_downtimes.html")


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

    assert request.user.is_authenticated

    check = get_object_or_404(Check.objects.select_related("project"), code=code)
    if request.user.is_superuser:
        return check, True

    if request.user.id == check.project.owner_id:
        return check, True

    membership = get_object_or_404(Member, project=check.project, user=request.user)
    return check, membership.rw


def _get_rw_check_for_user(request, code):
    check, rw = _get_check_for_user(request, code)
    if not rw:
        raise PermissionDenied

    return check


def _get_channel_for_user(request, code):
    """ Return specified channel if current user has access to it. """

    assert request.user.is_authenticated

    channel = get_object_or_404(Channel.objects.select_related("project"), code=code)
    if request.user.is_superuser:
        return channel, True

    if request.user.id == channel.project.owner_id:
        return channel, True

    membership = get_object_or_404(Member, project=channel.project, user=request.user)
    return channel, membership.rw


def _get_rw_channel_for_user(request, code):
    channel, rw = _get_channel_for_user(request, code)
    if not rw:
        raise PermissionDenied

    return channel


def _get_project_for_user(request, project_code):
    """ Check access, return (project, rw) tuple. """

    project = get_object_or_404(Project, code=project_code)
    if request.user.is_superuser:
        return project, True

    if request.user.id == project.owner_id:
        return project, True

    membership = get_object_or_404(Member, project=project, user=request.user)

    return project, membership.rw


def _get_rw_project_for_user(request, project_code):
    """ Check access, return (project, rw) tuple. """

    project, rw = _get_project_for_user(request, project_code)
    if not rw:
        raise PermissionDenied

    return project


def _refresh_last_active_date(profile):
    """ Update last_active_date if it is more than a day old. """

    now = timezone.now()
    if profile.last_active_date is None or (now - profile.last_active_date).days > 0:
        profile.last_active_date = now
        profile.save()


@login_required
def my_checks(request, code):
    _refresh_last_active_date(request.profile)
    project, rw = _get_project_for_user(request, code)

    if request.GET.get("sort") in VALID_SORT_VALUES:
        request.profile.sort = request.GET["sort"]
        request.profile.save()

    if request.session.get("last_project_id") != project.id:
        request.session["last_project_id"] = project.id

    q = Check.objects.filter(project=project)
    checks = list(q.prefetch_related("channel_set"))
    sortchecks(checks, request.profile.sort)

    tags_statuses, num_down = _tags_statuses(checks)
    pairs = list(tags_statuses.items())
    pairs.sort(key=lambda pair: pair[0].lower())

    channels = Channel.objects.filter(project=project)
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

    # Do we need to show the "Last Duration" header?
    show_last_duration = False
    for check in checks:
        if check.clamped_last_duration():
            show_last_duration = True
            break

    ctx = {
        "page": "checks",
        "rw": rw,
        "checks": checks,
        "channels": channels,
        "num_down": num_down,
        "tags": pairs,
        "ping_endpoint": settings.PING_ENDPOINT,
        "timezones": pytz.all_timezones,
        "project": project,
        "num_available": project.num_checks_available(),
        "sort": request.profile.sort,
        "selected_tags": selected_tags,
        "search": search,
        "hidden_checks": hidden_checks,
        "show_last_duration": show_last_duration,
    }

    return render(request, "front/my_checks.html", ctx)


@login_required
def status(request, code):
    _get_project_for_user(request, code)

    checks = list(Check.objects.filter(project__code=code))

    details = []
    for check in checks:
        ctx = {"check": check}
        details.append(
            {
                "code": str(check.code),
                "status": check.get_status(),
                "last_ping": LAST_PING_TMPL.render(ctx),
                "started": check.last_start is not None,
            }
        )

    tags_statuses, num_down = _tags_statuses(checks)
    return JsonResponse(
        {"details": details, "tags": tags_statuses, "title": num_down_title(num_down)}
    )


@login_required
@require_POST
def switch_channel(request, code, channel_code):
    check = _get_rw_check_for_user(request, code)

    channel = get_object_or_404(Channel, code=channel_code)
    if channel.project_id != check.project_id:
        return HttpResponseBadRequest()

    if request.POST.get("state") == "on":
        channel.checks.add(check)
    else:
        channel.checks.remove(check)

    return HttpResponse()


def index(request):
    if request.user.is_authenticated:
        projects = list(request.profile.projects())

        ctx = {
            "page": "projects",
            "projects": projects,
            "last_project_id": request.session.get("last_project_id"),
        }

        return render(request, "front/projects.html", ctx)

    check = Check()

    ctx = {
        "page": "welcome",
        "check": check,
        "ping_url": check.url(),
        "enable_apprise": settings.APPRISE_ENABLED is True,
        "enable_call": settings.TWILIO_AUTH is not None,
        "enable_discord": settings.DISCORD_CLIENT_ID is not None,
        "enable_linenotify": settings.LINENOTIFY_CLIENT_ID is not None,
        "enable_matrix": settings.MATRIX_ACCESS_TOKEN is not None,
        "enable_pdc": settings.PD_VENDOR_KEY is not None,
        "enable_pushbullet": settings.PUSHBULLET_CLIENT_ID is not None,
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None,
        "enable_shell": settings.SHELL_ENABLED is True,
        "enable_slack_btn": settings.SLACK_CLIENT_ID is not None,
        "enable_sms": settings.TWILIO_AUTH is not None,
        "enable_telegram": settings.TELEGRAM_TOKEN is not None,
        "enable_trello": settings.TRELLO_APP_KEY is not None,
        "enable_whatsapp": settings.TWILIO_USE_WHATSAPP,
        "registration_open": settings.REGISTRATION_OPEN,
    }

    return render(request, "front/welcome.html", ctx)


def dashboard(request):
    return render(request, "front/dashboard.html", {})


def serve_doc(request, doc="introduction"):
    path = os.path.join(settings.BASE_DIR, "templates/docs", doc + ".html")
    if not os.path.exists(path):
        raise Http404("not found")

    replaces = {
        "{{ default_timeout }}": str(int(DEFAULT_TIMEOUT.total_seconds())),
        "{{ default_grace }}": str(int(DEFAULT_GRACE.total_seconds())),
        "SITE_NAME": settings.SITE_NAME,
        "SITE_ROOT": settings.SITE_ROOT,
        "SITE_HOSTNAME": site_hostname(),
        "SITE_SCHEME": site_scheme(),
        "PING_ENDPOINT": settings.PING_ENDPOINT,
        "PING_URL": settings.PING_ENDPOINT + "your-uuid-here",
        "IMG_URL": os.path.join(settings.STATIC_URL, "img/docs"),
    }

    content = open(path, "r", encoding="utf-8").read()
    for placeholder, value in replaces.items():
        content = content.replace(placeholder, value)

    ctx = {
        "page": "docs",
        "section": doc,
        "content": content,
        "first_line": content.split("\n")[0],
    }

    return render(request, "front/docs_single.html", ctx)


def docs_cron(request):
    return render(request, "front/docs_cron.html", {})


@require_POST
@login_required
def add_check(request, code):
    project = _get_rw_project_for_user(request, code)
    if project.num_checks_available() <= 0:
        return HttpResponseBadRequest()

    check = Check(project=project)
    check.save()

    check.assign_all_channels()

    url = reverse("hc-details", args=[check.code])
    return redirect(url + "?new")


@require_POST
@login_required
def update_name(request, code):
    check = _get_rw_check_for_user(request, code)

    form = forms.NameTagsForm(request.POST)
    if form.is_valid():
        check.name = form.cleaned_data["name"]
        check.tags = form.cleaned_data["tags"]
        check.desc = form.cleaned_data["desc"]
        check.save()

    if "/details/" in request.META.get("HTTP_REFERER", ""):
        return redirect("hc-details", code)

    return redirect("hc-checks", check.project.code)


@require_POST
@login_required
def filtering_rules(request, code):
    check = _get_rw_check_for_user(request, code)

    form = forms.FilteringRulesForm(request.POST)
    if form.is_valid():
        check.subject = form.cleaned_data["subject"]
        check.subject_fail = form.cleaned_data["subject_fail"]
        check.methods = form.cleaned_data["methods"]
        check.manual_resume = form.cleaned_data["manual_resume"]
        check.save()

    return redirect("hc-details", code)


@require_POST
@login_required
def update_timeout(request, code):
    check = _get_rw_check_for_user(request, code)

    kind = request.POST.get("kind")
    if kind == "simple":
        form = forms.TimeoutForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "simple"
        check.timeout = form.cleaned_data["timeout"]
        check.grace = form.cleaned_data["grace"]
    elif kind == "cron":
        form = forms.CronForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "cron"
        check.schedule = form.cleaned_data["schedule"]
        check.tz = form.cleaned_data["tz"]
        check.grace = td(minutes=form.cleaned_data["grace"])

    check.alert_after = check.going_down_after()
    if check.status == "up" and check.alert_after < timezone.now():
        # Checks can flip from "up" to "down" state as a result of changing check's
        # schedule.  We don't want to send notifications when changing schedule
        # interactively in the web UI. So we update the `alert_after` and `status`
        # fields here the same way as `sendalerts` would do, but without sending
        # an actual alert:
        check.alert_after = None
        check.status = "down"

    check.save()

    if "/details/" in request.META.get("HTTP_REFERER", ""):
        return redirect("hc-details", code)

    return redirect("hc-checks", check.project.code)


@require_POST
def cron_preview(request):
    schedule = request.POST.get("schedule", "")
    tz = request.POST.get("tz")
    ctx = {"tz": tz, "dates": []}

    try:
        zone = pytz.timezone(tz)
        now_local = timezone.localtime(timezone.now(), zone)

        if len(schedule.split()) != 5:
            raise ValueError()

        it = croniter(schedule, now_local)
        for i in range(0, 6):
            ctx["dates"].append(it.get_next(datetime))

        ctx["desc"] = str(ExpressionDescriptor(schedule, use_24hour_time_format=True))
    except UnknownTimeZoneError:
        ctx["bad_tz"] = True
    except:
        ctx["bad_schedule"] = True

    return render(request, "front/cron_preview.html", ctx)


@login_required
def ping_details(request, code, n=None):
    check, rw = _get_check_for_user(request, code)
    q = Ping.objects.filter(owner=check)
    if n:
        q = q.filter(n=n)

    try:
        ping = q.latest("created")
    except Ping.DoesNotExist:
        return render(request, "front/ping_details_not_found.html")

    ctx = {"check": check, "ping": ping}

    return render(request, "front/ping_details.html", ctx)


@require_POST
@login_required
def pause(request, code):
    check = _get_rw_check_for_user(request, code)

    check.status = "paused"
    check.last_start = None
    check.alert_after = None
    check.save()

    # Don't redirect after an AJAX request:
    if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
        return HttpResponse()

    return redirect("hc-details", code)


@require_POST
@login_required
def resume(request, code):
    check = _get_rw_check_for_user(request, code)

    check.status = "new"
    check.last_start = None
    check.last_ping = None
    check.alert_after = None
    check.save()

    return redirect("hc-details", code)


@require_POST
@login_required
def remove_check(request, code):
    check = _get_rw_check_for_user(request, code)

    project = check.project
    check.delete()
    return redirect("hc-checks", project.code)


def _get_events(check, limit):
    pings = Ping.objects.filter(owner=check).order_by("-id")[:limit]
    pings = list(pings)

    prev = None
    for ping in reversed(pings):
        if ping.kind != "start" and prev and prev.kind == "start":
            delta = ping.created - prev.created
            if delta < MAX_DELTA:
                setattr(ping, "delta", delta)

        prev = ping

    alerts = []
    if len(pings):
        cutoff = pings[-1].created
        alerts = Notification.objects.select_related("channel").filter(
            owner=check, check_status="down", created__gt=cutoff
        )

    events = pings + list(alerts)
    events.sort(key=lambda el: el.created, reverse=True)
    return events


@login_required
def log(request, code):
    check, rw = _get_check_for_user(request, code)

    limit = check.project.owner_profile.ping_log_limit
    ctx = {
        "project": check.project,
        "check": check,
        "events": _get_events(check, limit),
        "limit": limit,
        "show_limit_notice": check.n_pings > limit and settings.USE_PAYMENTS,
    }

    return render(request, "front/log.html", ctx)


@login_required
def details(request, code):
    _refresh_last_active_date(request.profile)
    check, rw = _get_check_for_user(request, code)

    channels = Channel.objects.filter(project=check.project)
    channels = list(channels.order_by("created"))

    all_tags = set()
    q = Check.objects.filter(project=check.project).exclude(tags="")
    for tags in q.values_list("tags", flat=True):
        all_tags.update(tags.split(" "))

    ctx = {
        "page": "details",
        "project": check.project,
        "check": check,
        "rw": rw,
        "channels": channels,
        "enabled_channels": list(check.channel_set.all()),
        "timezones": pytz.all_timezones,
        "downtimes": check.downtimes(months=3),
        "is_new": "new" in request.GET,
        "is_copied": "copied" in request.GET,
        "all_tags": " ".join(sorted(all_tags)),
    }

    return render(request, "front/details.html", ctx)


@login_required
def transfer(request, code):
    check = _get_rw_check_for_user(request, code)

    if request.method == "POST":
        target_project = _get_rw_project_for_user(request, request.POST["project"])
        if target_project.num_checks_available() <= 0:
            return HttpResponseBadRequest()

        check.project = target_project
        check.save()
        check.assign_all_channels()

        messages.success(request, "Check transferred successfully!")
        return redirect("hc-details", code)

    ctx = {"check": check}
    return render(request, "front/transfer_modal.html", ctx)


@require_POST
@login_required
def copy(request, code):
    check = _get_rw_check_for_user(request, code)

    if check.project.num_checks_available() <= 0:
        return HttpResponseBadRequest()

    new_name = check.name + " (copy)"
    # Make sure we don't exceed the 100 character db field limit:
    if len(new_name) > 100:
        new_name = check.name[:90] + "... (copy)"

    copied = Check(project=check.project)
    copied.name = new_name
    copied.desc, copied.tags = check.desc, check.tags
    copied.subject, copied.subject_fail = check.subject, check.subject_fail
    copied.methods = check.methods
    copied.manual_resume = check.manual_resume

    copied.kind = check.kind
    copied.timeout, copied.grace = check.timeout, check.grace
    copied.schedule, copied.tz = check.schedule, check.tz
    copied.save()

    copied.channel_set.add(*check.channel_set.all())

    url = reverse("hc-details", args=[copied.code])
    return redirect(url + "?copied")


@login_required
def status_single(request, code):
    check, rw = _get_check_for_user(request, code)

    status = check.get_status()
    events = _get_events(check, 20)
    updated = "1"
    if len(events):
        updated = str(events[0].created.timestamp())

    doc = {
        "status": status,
        "status_text": STATUS_TEXT_TMPL.render({"check": check, "rw": rw}),
        "title": down_title(check),
        "updated": updated,
    }

    if updated != request.GET.get("u"):
        doc["events"] = EVENTS_TMPL.render({"check": check, "events": events})
        doc["downtimes"] = DOWNTIMES_TMPL.render({"downtimes": check.downtimes(3)})

    return JsonResponse(doc)


@login_required
def badges(request, code):
    project, rw = _get_project_for_user(request, code)

    tags = set()
    for check in Check.objects.filter(project=project):
        tags.update(check.tags_list())

    sorted_tags = sorted(tags, key=lambda s: s.lower())
    sorted_tags.append("*")  # For the "overall status" badge

    key = project.badge_key
    urls = []
    for tag in sorted_tags:
        urls.append(
            {
                "tag": tag,
                "svg": get_badge_url(key, tag),
                "svg3": get_badge_url(key, tag, with_late=True),
                "json": get_badge_url(key, tag, fmt="json"),
                "json3": get_badge_url(key, tag, fmt="json", with_late=True),
                "shields": get_badge_url(key, tag, fmt="shields"),
                "shields3": get_badge_url(key, tag, fmt="shields", with_late=True),
            }
        )

    ctx = {
        "have_tags": len(urls) > 1,
        "page": "badges",
        "project": project,
        "badges": urls,
    }

    return render(request, "front/badges.html", ctx)


@login_required
def channels(request, code):
    project, rw = _get_project_for_user(request, code)

    if request.method == "POST":
        if not rw:
            return HttpResponseForbidden()

        code = request.POST["channel"]
        try:
            channel = Channel.objects.get(code=code)
        except Channel.DoesNotExist:
            return HttpResponseBadRequest()
        if channel.project_id != project.id:
            return HttpResponseForbidden()

        new_checks = []
        for key in request.POST:
            if key.startswith("check-"):
                code = key[6:]
                try:
                    check = Check.objects.get(code=code)
                except Check.DoesNotExist:
                    return HttpResponseBadRequest()
                if check.project_id != project.id:
                    return HttpResponseForbidden()
                new_checks.append(check)

        channel.checks.set(new_checks)
        return redirect("hc-channels", project.code)

    channels = Channel.objects.filter(project=project)
    channels = channels.order_by("created")
    channels = channels.annotate(n_checks=Count("checks"))

    ctx = {
        "page": "channels",
        "rw": rw,
        "project": project,
        "profile": project.owner_profile,
        "channels": channels,
        "enable_apprise": settings.APPRISE_ENABLED is True,
        "enable_call": settings.TWILIO_AUTH is not None,
        "enable_discord": settings.DISCORD_CLIENT_ID is not None,
        "enable_linenotify": settings.LINENOTIFY_CLIENT_ID is not None,
        "enable_matrix": settings.MATRIX_ACCESS_TOKEN is not None,
        "enable_pdc": settings.PD_VENDOR_KEY is not None,
        "enable_pushbullet": settings.PUSHBULLET_CLIENT_ID is not None,
        "enable_pushover": settings.PUSHOVER_API_TOKEN is not None,
        "enable_shell": settings.SHELL_ENABLED is True,
        "enable_slack_btn": settings.SLACK_CLIENT_ID is not None,
        "enable_sms": settings.TWILIO_AUTH is not None,
        "enable_telegram": settings.TELEGRAM_TOKEN is not None,
        "enable_trello": settings.TRELLO_APP_KEY is not None,
        "enable_whatsapp": settings.TWILIO_USE_WHATSAPP,
        "use_payments": settings.USE_PAYMENTS,
    }

    return render(request, "front/channels.html", ctx)


@login_required
def channel_checks(request, code):
    channel = _get_rw_channel_for_user(request, code)

    assigned = set(channel.checks.values_list("code", flat=True).distinct())
    checks = Check.objects.filter(project=channel.project).order_by("created")

    ctx = {"checks": checks, "assigned": assigned, "channel": channel}

    return render(request, "front/channel_checks.html", ctx)


@require_POST
@login_required
def update_channel_name(request, code):
    channel = _get_rw_channel_for_user(request, code)

    form = forms.ChannelNameForm(request.POST)
    if form.is_valid():
        channel.name = form.cleaned_data["name"]
        channel.save()

    return redirect("hc-channels", channel.project.code)


def verify_email(request, code, token):
    channel = get_object_or_404(Channel, code=code)
    if channel.make_token() == token:
        channel.email_verified = True
        channel.save()
        return render(request, "front/verify_email_success.html")

    return render(request, "bad_link.html")


@csrf_exempt
def unsubscribe_email(request, code, signed_token):
    # Some email servers open links in emails to check for malicious content.
    # To work around this, on GET requests we serve a confirmation form.
    # If the signature is at least 5 minutes old, we also include JS code to
    # auto-submit the form.
    ctx = {}
    if ":" in signed_token:
        signer = signing.TimestampSigner(salt="alerts")
        # First, check the signature without looking at the timestamp:
        try:
            token = signer.unsign(signed_token)
        except signing.BadSignature:
            return render(request, "bad_link.html")

        # Check if timestamp is older than 5 minutes:
        try:
            signer.unsign(signed_token, max_age=300)
        except signing.SignatureExpired:
            ctx["autosubmit"] = True

    else:
        token = signed_token

    channel = get_object_or_404(Channel, code=code, kind="email")
    if channel.make_token() != token:
        return render(request, "bad_link.html")

    if request.method != "POST":
        return render(request, "accounts/unsubscribe_submit.html", ctx)

    channel.delete()
    return render(request, "front/unsubscribe_success.html")


@require_POST
@login_required
def send_test_notification(request, code):
    channel, rw = _get_channel_for_user(request, code)

    dummy = Check(name="TEST", status="down")
    dummy.last_ping = timezone.now() - td(days=1)
    dummy.n_pings = 42

    if channel.kind == "webhook" and not channel.url_down:
        if channel.url_up:
            # If we don't have url_down, but do have have url_up then
            # send "TEST is UP" notification instead:
            dummy.status = "up"

    # Delete all older test notifications for this channel
    Notification.objects.filter(channel=channel, owner=None).delete()

    # Send the test notification
    error = channel.notify(dummy, is_test=True)

    if error:
        messages.warning(request, "Could not send a test notification. %s" % error)
    else:
        messages.success(request, "Test notification sent!")

    return redirect("hc-channels", channel.project.code)


@require_POST
@login_required
def remove_channel(request, code):
    channel = _get_rw_channel_for_user(request, code)
    project = channel.project
    channel.delete()

    return redirect("hc-channels", project.code)


@login_required
def add_email(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddEmailForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="email")
            channel.value = json.dumps(
                {
                    "value": form.cleaned_data["value"],
                    "up": form.cleaned_data["up"],
                    "down": form.cleaned_data["down"],
                }
            )
            channel.save()

            channel.assign_all_checks()

            is_own_email = form.cleaned_data["value"] == request.user.email
            if is_own_email or not settings.EMAIL_USE_VERIFICATION:
                # If user is subscribing *their own* address
                # we can skip the verification step.

                # Additionally, in self-hosted setting, administator has the
                # option to disable the email verification step altogether.

                channel.email_verified = True
                channel.save()
            else:
                channel.send_verify_link()

            return redirect("hc-channels", project.code)
    else:
        form = forms.AddEmailForm()

    ctx = {
        "page": "channels",
        "project": project,
        "use_verification": settings.EMAIL_USE_VERIFICATION,
        "form": form,
    }
    return render(request, "integrations/add_email.html", ctx)


@login_required
def add_webhook(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.WebhookForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="webhook")
            channel.name = form.cleaned_data["name"]
            channel.value = form.get_value()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)

    else:
        form = forms.WebhookForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
    }
    return render(request, "integrations/webhook_form.html", ctx)


@login_required
def edit_webhook(request, code):
    channel = _get_rw_channel_for_user(request, code)
    if channel.kind != "webhook":
        return HttpResponseBadRequest()

    if request.method == "POST":
        form = forms.WebhookForm(request.POST)
        if form.is_valid():
            channel.name = form.cleaned_data["name"]
            channel.value = form.get_value()
            channel.save()

            return redirect("hc-channels", channel.project.code)
    else:

        def flatten(d):
            return "\n".join("%s: %s" % pair for pair in d.items())

        doc = json.loads(channel.value)
        doc["headers_down"] = flatten(doc["headers_down"])
        doc["headers_up"] = flatten(doc["headers_up"])
        doc["name"] = channel.name

        form = forms.WebhookForm(doc)

    ctx = {
        "page": "channels",
        "project": channel.project,
        "channel": channel,
        "form": form,
    }
    return render(request, "integrations/webhook_form.html", ctx)


@require_setting("SHELL_ENABLED")
@login_required
def add_shell(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.AddShellForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="shell")
            channel.value = form.get_value()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddShellForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
    }
    return render(request, "integrations/add_shell.html", ctx)


@login_required
def add_pd(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddPdForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="pd")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddPdForm()

    ctx = {"page": "channels", "form": form}
    return render(request, "integrations/add_pd.html", ctx)


@require_setting("PD_VENDOR_KEY")
def pdc_help(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_pdc.html", ctx)


@require_setting("PD_VENDOR_KEY")
@login_required
def add_pdc(request, code):
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    callback = settings.SITE_ROOT + reverse(
        "hc-add-pdc-complete", args=[project.code, state]
    )
    connect_url = "https://connect.pagerduty.com/connect?" + urlencode(
        {"vendor": settings.PD_VENDOR_KEY, "callback": callback}
    )

    ctx = {"page": "channels", "project": project, "connect_url": connect_url}
    request.session["pd"] = state
    return render(request, "integrations/add_pdc.html", ctx)


@require_setting("PD_VENDOR_KEY")
@login_required
def add_pdc_complete(request, code, state):
    if "pd" not in request.session:
        return HttpResponseBadRequest()

    project = _get_rw_project_for_user(request, code)

    session_state = request.session.pop("pd")
    if session_state != state:
        return HttpResponseBadRequest()

    if request.GET.get("error") == "cancelled":
        messages.warning(request, "PagerDuty setup was cancelled.")
        return redirect("hc-channels", project.code)

    channel = Channel(kind="pd", project=project)
    channel.value = json.dumps(
        {
            "service_key": request.GET.get("service_key"),
            "account": request.GET.get("account"),
        }
    )
    channel.save()
    channel.assign_all_checks()
    messages.success(request, "The PagerDuty integration has been added!")
    return redirect("hc-channels", project.code)


@login_required
def add_pagertree(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="pagertree")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_pagertree.html", ctx)


@login_required
def add_slack(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="slack")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {
        "page": "channels",
        "form": form,
    }

    return render(request, "integrations/add_slack.html", ctx)


@require_setting("SLACK_CLIENT_ID")
def slack_help(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_slack_btn.html", ctx)


@require_setting("SLACK_CLIENT_ID")
@login_required
def add_slack_btn(request, code):
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    authorize_url = "https://slack.com/oauth/v2/authorize?" + urlencode(
        {
            "scope": "incoming-webhook",
            "client_id": settings.SLACK_CLIENT_ID,
            "state": state,
        }
    )

    ctx = {
        "project": project,
        "page": "channels",
        "authorize_url": authorize_url,
    }

    request.session["add_slack"] = (state, str(project.code))
    return render(request, "integrations/add_slack_btn.html", ctx)


@require_setting("SLACK_CLIENT_ID")
@login_required
def add_slack_complete(request):
    if "add_slack" not in request.session:
        return HttpResponseForbidden()

    state, code = request.session.pop("add_slack")
    project = _get_rw_project_for_user(request, code)
    if request.GET.get("error") == "access_denied":
        messages.warning(request, "Slack setup was cancelled.")
        return redirect("hc-channels", project.code)

    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    result = requests.post(
        "https://slack.com/api/oauth.v2.access",
        {
            "client_id": settings.SLACK_CLIENT_ID,
            "client_secret": settings.SLACK_CLIENT_SECRET,
            "code": request.GET.get("code"),
        },
    )

    doc = result.json()
    if doc.get("ok"):
        channel = Channel(kind="slack", project=project)
        channel.value = result.text
        channel.save()
        channel.assign_all_checks()
        messages.success(request, "The Slack integration has been added!")
    else:
        s = doc.get("error")
        messages.warning(request, "Error message from slack: %s" % s)

    return redirect("hc-channels", project.code)


@login_required
def add_mattermost(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="mattermost")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "form": form, "project": project}
    return render(request, "integrations/add_mattermost.html", ctx)


@require_setting("PUSHBULLET_CLIENT_ID")
@login_required
def add_pushbullet(request, code):
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    authorize_url = "https://www.pushbullet.com/authorize?" + urlencode(
        {
            "client_id": settings.PUSHBULLET_CLIENT_ID,
            "redirect_uri": settings.SITE_ROOT + reverse(add_pushbullet_complete),
            "response_type": "code",
            "state": state,
        }
    )

    ctx = {
        "page": "channels",
        "project": project,
        "authorize_url": authorize_url,
    }

    request.session["add_pushbullet"] = (state, str(project.code))
    return render(request, "integrations/add_pushbullet.html", ctx)


@require_setting("PUSHBULLET_CLIENT_ID")
@login_required
def add_pushbullet_complete(request):
    if "add_pushbullet" not in request.session:
        return HttpResponseForbidden()

    state, code = request.session.pop("add_pushbullet")
    project = _get_rw_project_for_user(request, code)

    if request.GET.get("error") == "access_denied":
        messages.warning(request, "Pushbullet setup was cancelled.")
        return redirect("hc-channels", project.code)

    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    result = requests.post(
        "https://api.pushbullet.com/oauth2/token",
        {
            "client_id": settings.PUSHBULLET_CLIENT_ID,
            "client_secret": settings.PUSHBULLET_CLIENT_SECRET,
            "code": request.GET.get("code"),
            "grant_type": "authorization_code",
        },
    )

    doc = result.json()
    if "access_token" in doc:
        channel = Channel(kind="pushbullet", project=project)
        channel.value = doc["access_token"]
        channel.save()
        channel.assign_all_checks()
        messages.success(request, "The Pushbullet integration has been added!")
    else:
        messages.warning(request, "Something went wrong")

    return redirect("hc-channels", project.code)


@require_setting("DISCORD_CLIENT_ID")
@login_required
def add_discord(request, code):
    project = _get_rw_project_for_user(request, code)
    state = token_urlsafe()
    auth_url = "https://discordapp.com/api/oauth2/authorize?" + urlencode(
        {
            "client_id": settings.DISCORD_CLIENT_ID,
            "scope": "webhook.incoming",
            "redirect_uri": settings.SITE_ROOT + reverse(add_discord_complete),
            "response_type": "code",
            "state": state,
        }
    )

    ctx = {"page": "channels", "project": project, "authorize_url": auth_url}

    request.session["add_discord"] = (state, str(project.code))
    return render(request, "integrations/add_discord.html", ctx)


@require_setting("DISCORD_CLIENT_ID")
@login_required
def add_discord_complete(request):
    if "add_discord" not in request.session:
        return HttpResponseForbidden()

    state, code = request.session.pop("add_discord")
    project = _get_rw_project_for_user(request, code)

    if request.GET.get("error") == "access_denied":
        messages.warning(request, "Discord setup was cancelled.")
        return redirect("hc-channels", project.code)

    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    result = requests.post(
        "https://discordapp.com/api/oauth2/token",
        {
            "client_id": settings.DISCORD_CLIENT_ID,
            "client_secret": settings.DISCORD_CLIENT_SECRET,
            "code": request.GET.get("code"),
            "grant_type": "authorization_code",
            "redirect_uri": settings.SITE_ROOT + reverse(add_discord_complete),
        },
    )

    doc = result.json()
    if "access_token" in doc:
        channel = Channel(kind="discord", project=project)
        channel.value = result.text
        channel.save()
        channel.assign_all_checks()
        messages.success(request, "The Discord integration has been added!")
    else:
        messages.warning(request, "Something went wrong.")

    return redirect("hc-channels", project.code)


@require_setting("PUSHOVER_API_TOKEN")
def pushover_help(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_pushover_help.html", ctx)


@require_setting("PUSHOVER_API_TOKEN")
@login_required
def add_pushover(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        state = token_urlsafe()

        failure_url = settings.SITE_ROOT + reverse("hc-channels", args=[project.code])
        success_url = (
            settings.SITE_ROOT
            + reverse("hc-add-pushover", args=[project.code])
            + "?"
            + urlencode(
                {
                    "state": state,
                    "prio": request.POST.get("po_priority", "0"),
                    "prio_up": request.POST.get("po_priority_up", "0"),
                }
            )
        )
        subscription_url = (
            settings.PUSHOVER_SUBSCRIPTION_URL
            + "?"
            + urlencode({"success": success_url, "failure": failure_url})
        )

        request.session["pushover"] = state
        return redirect(subscription_url)

    # Handle successful subscriptions
    if "pushover_user_key" in request.GET:
        if "pushover" not in request.session:
            return HttpResponseForbidden()

        state = request.session.pop("pushover")
        if request.GET.get("state") != state:
            return HttpResponseForbidden()

        if request.GET.get("pushover_unsubscribed") == "1":
            # Unsubscription: delete all Pushover channels for this project
            Channel.objects.filter(project=project, kind="po").delete()
            return redirect("hc-channels", project.code)

        form = forms.AddPushoverForm(request.GET)
        if not form.is_valid():
            return HttpResponseBadRequest()

        channel = Channel(project=project, kind="po")
        channel.value = form.get_value()
        channel.save()
        channel.assign_all_checks()

        messages.success(request, "The Pushover integration has been added!")
        return redirect("hc-channels", project.code)

    # Show Integration Settings form
    ctx = {
        "page": "channels",
        "project": project,
        "po_retry_delay": td(seconds=settings.PUSHOVER_EMERGENCY_RETRY_DELAY),
        "po_expiration": td(seconds=settings.PUSHOVER_EMERGENCY_EXPIRATION),
    }
    return render(request, "integrations/add_pushover.html", ctx)


@login_required
def add_opsgenie(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddOpsGenieForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="opsgenie")
            v = {"region": form.cleaned_data["region"], "key": form.cleaned_data["key"]}
            channel.value = json.dumps(v)
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddOpsGenieForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_opsgenie.html", ctx)


@login_required
def add_victorops(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="victorops")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_victorops.html", ctx)


@login_required
def add_zulip(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddZulipForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="zulip")
            channel.value = form.get_value()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddZulipForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_zulip.html", ctx)


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

    invite = render_to_string(
        "integrations/telegram_invite.html",
        {"qs": signing.dumps((chat["id"], chat["type"], name))},
    )

    Telegram.send(chat["id"], invite)
    return HttpResponse()


@require_setting("TELEGRAM_TOKEN")
def telegram_help(request):
    ctx = {
        "page": "channels",
        "bot_name": settings.TELEGRAM_BOT_NAME,
    }

    return render(request, "integrations/add_telegram.html", ctx)


@require_setting("TELEGRAM_TOKEN")
@login_required
def add_telegram(request):
    chat_id, chat_type, chat_name = None, None, None
    qs = request.META["QUERY_STRING"]
    if qs:
        try:
            chat_id, chat_type, chat_name = signing.loads(qs, max_age=600)
        except signing.BadSignature:
            return render(request, "bad_link.html")

    if request.method == "POST":
        project = _get_rw_project_for_user(request, request.POST.get("project"))
        channel = Channel(project=project, kind="telegram")
        channel.value = json.dumps(
            {"id": chat_id, "type": chat_type, "name": chat_name}
        )
        channel.save()

        channel.assign_all_checks()
        messages.success(request, "The Telegram integration has been added!")
        return redirect("hc-channels", project.code)

    ctx = {
        "page": "channels",
        "projects": request.profile.projects(),
        "chat_id": chat_id,
        "chat_type": chat_type,
        "chat_name": chat_name,
        "bot_name": settings.TELEGRAM_BOT_NAME,
    }

    return render(request, "integrations/add_telegram.html", ctx)


@require_setting("TWILIO_AUTH")
@login_required
def add_sms(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.AddSmsForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="sms")
            channel.name = form.cleaned_data["label"]
            channel.value = json.dumps({"value": form.cleaned_data["value"]})
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddSmsForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
        "profile": project.owner_profile,
    }
    return render(request, "integrations/add_sms.html", ctx)


@require_setting("TWILIO_AUTH")
@login_required
def add_call(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.AddSmsForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="call")
            channel.name = form.cleaned_data["label"]
            channel.value = json.dumps({"value": form.cleaned_data["value"]})
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddSmsForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
        "profile": project.owner_profile,
    }
    return render(request, "integrations/add_call.html", ctx)


@require_setting("TWILIO_USE_WHATSAPP")
@login_required
def add_whatsapp(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.AddSmsForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="whatsapp")
            channel.name = form.cleaned_data["label"]
            channel.value = json.dumps(
                {
                    "value": form.cleaned_data["value"],
                    "up": form.cleaned_data["up"],
                    "down": form.cleaned_data["down"],
                }
            )
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddSmsForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
        "profile": project.owner_profile,
    }
    return render(request, "integrations/add_whatsapp.html", ctx)


@require_setting("TRELLO_APP_KEY")
@login_required
def add_trello(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        channel = Channel(project=project, kind="trello")
        channel.value = request.POST["settings"]
        channel.save()

        channel.assign_all_checks()
        return redirect("hc-channels", project.code)

    return_url = settings.SITE_ROOT + reverse("hc-add-trello", args=[project.code])
    authorize_url = "https://trello.com/1/authorize?" + urlencode(
        {
            "expiration": "never",
            "name": settings.SITE_NAME,
            "scope": "read,write",
            "response_type": "token",
            "key": settings.TRELLO_APP_KEY,
            "return_url": return_url,
        }
    )

    ctx = {
        "page": "channels",
        "project": project,
        "authorize_url": authorize_url,
    }

    return render(request, "integrations/add_trello.html", ctx)


@require_setting("MATRIX_ACCESS_TOKEN")
@login_required
def add_matrix(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.AddMatrixForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="matrix")
            channel.value = form.cleaned_data["room_id"]

            # If user supplied room alias instead of ID, use it as channel name
            alias = form.cleaned_data["alias"]
            if not alias.startswith("!"):
                channel.name = alias

            channel.save()

            channel.assign_all_checks()
            messages.success(request, "The Matrix integration has been added!")
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddMatrixForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
        "matrix_user_id": settings.MATRIX_USER_ID,
    }
    return render(request, "integrations/add_matrix.html", ctx)


@require_setting("APPRISE_ENABLED")
@login_required
def add_apprise(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddAppriseForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="apprise")
            channel.value = form.cleaned_data["url"]
            channel.save()

            channel.assign_all_checks()
            messages.success(request, "The Apprise integration has been added!")
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddAppriseForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_apprise.html", ctx)


@require_setting("TRELLO_APP_KEY")
@login_required
@require_POST
def trello_settings(request):
    token = request.POST.get("token")

    url = "https://api.trello.com/1/members/me/boards?" + urlencode(
        {
            "key": settings.TRELLO_APP_KEY,
            "token": token,
            "fields": "id,name",
            "lists": "open",
            "list_fields": "id,name",
        }
    )

    r = requests.get(url)
    ctx = {"token": token, "data": r.json()}
    return render(request, "integrations/trello_settings.html", ctx)


@login_required
def add_msteams(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="msteams")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_msteams.html", ctx)


@login_required
def add_prometheus(request, code):
    project, rw = _get_project_for_user(request, code)
    ctx = {"page": "channels", "project": project}
    return render(request, "integrations/add_prometheus.html", ctx)


def metrics(request, code, key):
    if len(key) != 32:
        return HttpResponseBadRequest()

    q = Project.objects.filter(code=code, api_key_readonly=key)
    try:
        project = q.get()
    except Project.DoesNotExist:
        return HttpResponseForbidden()

    checks = Check.objects.filter(project_id=project.id).order_by("id")

    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def output(checks):
        yield "# HELP hc_check_up Whether the check is currently up (1 for yes, 0 for no).\n"
        yield "# TYPE hc_check_up gauge\n"

        TMPL = """hc_check_up{name="%s", tags="%s", unique_key="%s"} %d\n"""
        for check in checks:
            value = 0 if check.get_status() == "down" else 1
            yield TMPL % (esc(check.name), esc(check.tags), check.unique_key, value)

        tags_statuses, num_down = _tags_statuses(checks)
        yield "\n"
        yield "# HELP hc_tag_up Whether all checks with this tag are up (1 for yes, 0 for no).\n"
        yield "# TYPE hc_tag_up gauge\n"
        TMPL = """hc_tag_up{tag="%s"} %d\n"""
        for tag in sorted(tags_statuses):
            value = 0 if tags_statuses[tag] == "down" else 1
            yield TMPL % (esc(tag), value)

        yield "\n"
        yield "# HELP hc_checks_total The total number of checks.\n"
        yield "# TYPE hc_checks_total gauge\n"
        yield "hc_checks_total %d\n" % len(checks)
        yield "\n"

        yield "# HELP hc_checks_down_total The number of checks currently down.\n"
        yield "# TYPE hc_checks_down_total gauge\n"
        yield "hc_checks_down_total %d\n" % num_down

    return HttpResponse(output(checks), content_type="text/plain")


@login_required
def add_spike(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="spike")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_spike.html", ctx)


@require_setting("LINENOTIFY_CLIENT_ID")
@login_required
def add_linenotify(request, code):
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    authorize_url = " https://notify-bot.line.me/oauth/authorize?" + urlencode(
        {
            "client_id": settings.LINENOTIFY_CLIENT_ID,
            "redirect_uri": settings.SITE_ROOT + reverse(add_linenotify_complete),
            "response_type": "code",
            "state": state,
            "scope": "notify",
        }
    )

    ctx = {
        "page": "channels",
        "project": project,
        "authorize_url": authorize_url,
    }

    request.session["add_linenotify"] = (state, str(project.code))
    return render(request, "integrations/add_linenotify.html", ctx)


@require_setting("LINENOTIFY_CLIENT_ID")
@login_required
def add_linenotify_complete(request):
    if "add_linenotify" not in request.session:
        return HttpResponseForbidden()

    state, code = request.session.pop("add_linenotify")
    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    project = _get_rw_project_for_user(request, code)
    if request.GET.get("error") == "access_denied":
        messages.warning(request, "LINE Notify setup was cancelled.")
        return redirect("hc-channels", project.code)

    # Exchange code for access token
    result = requests.post(
        "https://notify-bot.line.me/oauth/token",
        {
            "grant_type": "authorization_code",
            "code": request.GET.get("code"),
            "redirect_uri": settings.SITE_ROOT + reverse(add_linenotify_complete),
            "client_id": settings.LINENOTIFY_CLIENT_ID,
            "client_secret": settings.LINENOTIFY_CLIENT_SECRET,
        },
    )

    doc = result.json()
    if doc.get("status") != 200:
        messages.warning(request, "Something went wrong.")
        return redirect("hc-channels", project.code)

    # Fetch notification target's name, will use it as channel name:
    token = doc["access_token"]
    result = requests.get(
        "https://notify-api.line.me/api/status",
        headers={"Authorization": "Bearer %s" % token},
    )
    doc = result.json()

    channel = Channel(kind="linenotify", project=project)
    channel.name = doc.get("target")
    channel.value = token
    channel.save()
    channel.assign_all_checks()
    messages.success(request, "The LINE Notify integration has been added!")

    return redirect("hc-channels", project.code)


# Forks: add custom views after this line
