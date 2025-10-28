from __future__ import annotations

import email
import logging
import os
import re
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime
from datetime import timedelta as td
from itertools import islice
from typing import TypedDict, cast
from urllib.parse import urlencode, urlparse
from uuid import UUID
from zoneinfo import ZoneInfo

from cronsim import CronSim
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Case, Count, F, Q, When
from django.db.models.functions import Substr
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_stubs_ext import WithAnnotations
from hc.accounts.http import AuthenticatedHttpRequest
from hc.accounts.models import Member, Profile, Project
from hc.api.models import (
    DEFAULT_GRACE,
    DEFAULT_TIMEOUT,
    MAX_DURATION,
    Channel,
    Check,
    Flip,
    Notification,
    Ping,
)
from hc.front import forms
from hc.front.templatetags.hc_extras import (
    down_title,
    num_down_title,
    site_hostname,
    sortchecks,
)
from hc.front.validators import CronValidator, OnCalendarValidator
from hc.lib.badges import get_badge_url
from hc.lib.tz import all_timezones
from hc.lib.urls import absolute_reverse
from oncalendar import OnCalendar, OnCalendarError

logger = logging.getLogger(__name__)

VALID_SORT_VALUES = ("name", "-name", "last_ping", "-last_ping", "created")
STATUS_TEXT_TMPL = get_template("front/log_status_text.html")
LAST_PING_TMPL = get_template("front/last_ping_cell.html")
EVENTS_TMPL = get_template("front/details_events.html")
DOWNTIMES_TMPL = get_template("front/details_downtimes.html")


def _tags_counts(checks: Iterable[Check]) -> tuple[list[tuple[str, str, str]], int]:
    num_down = 0
    grace = set()
    counts: Counter[str] = Counter()
    down_counts: Counter[str] = Counter()
    for check in checks:
        counts.update(check.tags_list())
        if check.cached_status == "down":
            num_down += 1
            down_counts.update(check.tags_list())
        elif check.cached_status == "grace":
            grace.update(check.tags_list())

    result = []
    for tag in counts:
        if tag in down_counts:
            status = "down"
            text = f"{down_counts[tag]} of {counts[tag]} down"
        else:
            status = "grace" if tag in grace else "up"
            text = f"{counts[tag]} up"

        result.append((tag, status, text))

    return result, num_down


def _common_timezones(checks: Iterable[Check]) -> list[str]:
    counter: Counter[str] = Counter()
    for check in checks:
        counter[check.tz] += 1

    return [tz for tz, _ in counter.most_common(3)]


def _get_check_for_user(
    request: HttpRequest, code: UUID, preload_owner_profile: bool = False
) -> tuple[Check, bool]:
    """Return specified check if current user has access to it.

    If `preload_owner_profile` is `True`, the returned check's
    project.owner.profile will be already loaded. This helps avoid extra SQL queries
    if the caller later looks up the project owner's check_limit or ping_log_limit.

    """

    assert request.user.is_authenticated

    q = Check.objects.select_related("project")
    if preload_owner_profile:
        q = q.select_related("project__owner__profile")

    check = get_object_or_404(q, code=code)
    if request.user.is_superuser:
        return check, True

    if request.user.id == check.project.owner_id:
        return check, True

    membership = get_object_or_404(Member, project=check.project, user=request.user)
    return check, membership.is_rw


def _get_rw_check_for_user(request: HttpRequest, code: UUID) -> Check:
    check, rw = _get_check_for_user(request, code)
    if not rw:
        raise PermissionDenied

    return check


def _get_channel_for_user(request: HttpRequest, code: UUID) -> tuple[Channel, bool]:
    """Return specified channel if current user has access to it."""

    assert request.user.is_authenticated

    channel = get_object_or_404(Channel.objects.select_related("project"), code=code)
    if request.user.is_superuser:
        return channel, True

    if request.user.id == channel.project.owner_id:
        return channel, True

    membership = get_object_or_404(Member, project=channel.project, user=request.user)
    return channel, membership.is_rw


def _get_rw_channel_for_user(request: HttpRequest, code: UUID) -> Channel:
    channel, rw = _get_channel_for_user(request, code)
    if not rw:
        raise PermissionDenied

    return channel


def _get_project_for_user(request: HttpRequest, code: UUID) -> tuple[Project, bool]:
    """Check access, return (project, rw) tuple."""

    project = get_object_or_404(Project, code=code)
    if request.user.is_superuser:
        return project, True

    if request.user.id == project.owner_id:
        return project, True

    membership = get_object_or_404(Member, project=project, user=request.user)

    return project, membership.is_rw


def _get_rw_project_for_user(request: HttpRequest, code: UUID) -> Project:
    """Check access, return (project, rw) tuple."""

    project, rw = _get_project_for_user(request, code)
    if not rw:
        raise PermissionDenied

    return project


def _refresh_last_active_date(request: AuthenticatedHttpRequest) -> None:
    """Update last_active_date if it is more than a day old."""

    profile = request.profile
    if profile.last_active_date is None or (now() - profile.last_active_date).days > 0:
        profile.last_active_date = now()
        profile.save()

        # Also modify session to trigger session cookie refresh
        # and push forward its expiry date:
        request.session["last_active"] = profile.last_active_date.timestamp()

    return None


def _get_referer_qs(request: HttpRequest) -> str:
    parsed = urlparse(request.headers.get("Referer", ""))
    if parsed.query:
        return "?" + parsed.query
    return ""


def _status_match(check: Check, statuses: set[str]) -> bool:
    if "started" in statuses and check.last_start:
        return True
    return check.cached_status in statuses


@login_required
def checks(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    _refresh_last_active_date(request)
    project, rw = _get_project_for_user(request, code)

    if request.GET.get("sort") in VALID_SORT_VALUES:
        request.profile.sort = request.GET["sort"]
        request.profile.save()

    if request.GET.get("urls") in ("uuid", "slug") and rw:
        project.show_slugs = request.GET["urls"] == "slug"
        project.save()

    if request.session.get("last_project_id") != project.id:
        request.session["last_project_id"] = project.id

    q = Check.objects.filter(project=project)
    q = q.select_related("project")
    checks = list(q.prefetch_related("channel_set"))
    sortchecks(checks, request.profile.sort)

    tags_counts, num_down = _tags_counts(checks)
    tags_counts.sort(key=lambda item: item[0].lower())

    is_group = Case(When(kind="group", then=0), default=1)
    channels = project.channel_set.annotate(is_group=is_group)
    # Sort groups first, then in the creation order
    channels = channels.order_by("is_group", "created")

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
            haystack = f"{check.name}\n{check.slug}\n{check.code}"
            if search not in haystack.lower():
                hidden_checks.add(check)

    # Hide checks that don't match status filters
    selected_statuses = set(request.GET.getlist("status", []))
    if selected_statuses:
        for check in checks:
            if not _status_match(check, selected_statuses):
                hidden_checks.add(check)

    # Figure out which checks have ambiguous ping URLs
    seen, ambiguous = set(), set()
    if project.show_slugs:
        for check in checks:
            if check.slug and check.slug in seen:
                ambiguous.add(check.slug)
            else:
                seen.add(check.slug)

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
        "tags": tags_counts,
        "ping_endpoint": settings.PING_ENDPOINT,
        "common_timezones": _common_timezones(checks),
        "timezones": all_timezones,
        "project": project,
        "num_available": project.num_checks_available(),
        "sort": request.profile.sort,
        "selected_tags": selected_tags,
        "selected_statuses": selected_statuses,
        "search": search,
        "hidden_checks": hidden_checks,
        "num_visible": len(checks) - len(hidden_checks),
        "ambiguous": ambiguous,
        "show_last_duration": show_last_duration,
    }

    return render(request, "front/checks.html", ctx)


def status(request: HttpRequest, code: UUID) -> HttpResponse:
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    project, rw = _get_project_for_user(request, code)
    checks = list(Check.objects.filter(project=project))

    details = []
    for check in checks:
        ctx = {"check": check}
        details.append(
            {
                "code": str(check.code),
                "status": check.get_status(),
                "last_ping": LAST_PING_TMPL.render(ctx).strip(),
                "started": check.last_start is not None,
            }
        )

    tags_counts, num_down = _tags_counts(checks)
    tags = {tag: (status, tooltip) for tag, status, tooltip in tags_counts}
    return JsonResponse(
        {"details": details, "tags": tags, "title": num_down_title(num_down)}
    )


@login_required
@require_POST
def switch_channel(
    request: AuthenticatedHttpRequest, code: UUID, channel_code: UUID
) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    channel = get_object_or_404(Channel, code=channel_code)
    if channel.project_id != check.project_id:
        return HttpResponseBadRequest()

    if request.POST.get("state") == "on":
        channel.checks.add(check)
    else:
        channel.checks.remove(check)

    return HttpResponse()


class ProjectStatus(TypedDict):
    status: str
    started: bool


def _get_project_summary(profile: Profile) -> dict[UUID, ProjectStatus]:
    statuses: dict[UUID, ProjectStatus] = defaultdict(
        lambda: {"status": "up", "started": False}
    )
    q = profile.checks_from_all_projects()
    q = q.annotate(project_code=F("project__code"))
    for check in q:
        summary = statuses[check.project_code]
        if check.last_start:
            summary["started"] = True

        if summary["status"] != "down":
            status = check.get_status()
            if status == "down" or (status == "grace" and summary["status"] == "up"):
                summary["status"] = status

    return statuses


def index(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("hc-login")

    # We now know user is logged, tell the type checker request.profile exists-
    request = cast(AuthenticatedHttpRequest, request)
    _refresh_last_active_date(request)
    summary = _get_project_summary(request.profile)
    if "refresh" in request.GET:
        return JsonResponse({str(k): v for k, v in summary.items()})

    q = request.profile.projects()
    q = q.annotate(n_checks=Count("check", distinct=True))
    q = q.annotate(n_channels=Count("channel", distinct=True))
    q = q.annotate(owner_email=F("owner__email"))
    projects = list(q)
    any_down = False
    for project in projects:
        setattr(project, "overall_status", summary[project.code]["status"])
        setattr(project, "any_started", summary[project.code]["started"])
        if summary[project.code]["status"] == "down":
            any_down = True

    # The list returned by projects() is already sorted . Do an additional sorting pass
    # to move projects with overall_status=down to the front (without changing their
    # relative order)
    projects.sort(key=lambda p: getattr(p, "overall_status") != "down")
    ctx = {
        "page": "projects",
        "projects": projects,
        "last_project_id": request.session.get("last_project_id"),
        "any_down": any_down,
    }

    return render(request, "front/projects.html", ctx)


@login_required
def projects_menu(request: AuthenticatedHttpRequest) -> HttpResponse:
    projects = list(request.profile.projects())

    statuses: dict[int, str] = defaultdict(lambda: "up")
    for check in Check.objects.filter(project__in=projects):
        old_status = statuses[check.project_id]
        if old_status != "down":
            status = check.get_status()
            if status == "down" or (status == "grace" and old_status == "up"):
                statuses[check.project_id] = status

    for p in projects:
        setattr(p, "overall_status", statuses[p.id])

    return render(request, "front/projects_menu.html", {"projects": projects})


def dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "front/dashboard.html", {})


def _replace_placeholders(doc: str, html: str) -> str:
    if doc.startswith("self_hosted"):
        return html

    limit = settings.PING_BODY_LIMIT or 100
    if limit % 1000 == 0:
        limit_fmt = f"{limit // 1000} kB"
    else:
        limit_fmt = f"{limit} bytes"

    replaces = {
        "{{ default_timeout }}": str(int(DEFAULT_TIMEOUT.total_seconds())),
        "{{ default_grace }}": str(int(DEFAULT_GRACE.total_seconds())),
        "SITE_NAME": settings.SITE_NAME,
        "SITE_ROOT": settings.SITE_ROOT,
        "SITE_HOSTNAME": site_hostname(),
        "SITE_SCHEME": urlparse(settings.SITE_ROOT).scheme,
        "PING_ENDPOINT": settings.PING_ENDPOINT,
        "PING_URL": settings.PING_ENDPOINT + "your-uuid-here",
        "PING_BODY_LIMIT_FORMATTED": limit_fmt,
        "PING_BODY_LIMIT": str(limit),
        "IMG_URL": os.path.join(settings.STATIC_URL, "img/docs"),
    }

    for placeholder, value in replaces.items():
        html = html.replace(placeholder, value)

    return html


def serve_doc(request: HttpRequest, doc: str = "introduction") -> HttpResponse:
    # Filenames in /templates/docs/ consist of lowercase letters and underscores,
    # -- make sure we don't accept anything else
    if not re.match(r"^[0-9a-z_]+$", doc):
        raise Http404("not found")

    path = settings.BASE_DIR / f"templates/docs/{doc}.html-fragment"
    if not path.exists():
        raise Http404("not found")

    with path.open("r", encoding="utf-8") as f:
        content = f.read()

    content = _replace_placeholders(doc, content)
    ctx = {
        "page": "docs",
        "section": doc,
        "content": content,
        "first_line": content.split("\n")[0],
    }

    return render(request, "front/docs_single.html", ctx)


@csrf_exempt
def docs_search(request: HttpRequest) -> HttpResponse:
    form = forms.SearchForm(request.GET)
    if not form.is_valid():
        return render(request, "front/docs_search.html", {"results": []})

    query = """
        SELECT slug, title, snippet(docs, 2, '<span>', '</span>', '&hellip;', 10)
        FROM docs
        WHERE docs MATCH ?
        ORDER BY bm25(docs, 2.0, 10.0, 1.0)
        LIMIT 8
    """

    # Wrap the query in double quotes to get a valid FTS string
    # https://www.sqlite.org/fts5.html#full_text_query_syntax
    q = '"%s"' % form.cleaned_data["q"]
    con = sqlite3.connect(settings.BASE_DIR / "search.db")
    cur = con.cursor()
    res = cur.execute(query, (q,))

    ctx = {"results": res.fetchall()}
    return render(request, "front/docs_search.html", ctx)


def docs_cron(request: HttpRequest) -> HttpResponse:
    return render(request, "front/docs_cron.html", {"page": "docs-cron"})


@require_POST
@login_required
def add_check(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    if project.num_checks_available() <= 0:
        return HttpResponseBadRequest()

    form = forms.AddCheckForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest()

    check = Check(project=project)
    check.name = form.cleaned_data["name"]
    check.slug = form.cleaned_data["slug"]
    check.tags = form.cleaned_data["tags"]
    check.kind = form.cleaned_data["kind"]
    check.timeout = form.cleaned_data["timeout"]
    check.schedule = form.cleaned_data["schedule"]
    check.tz = form.cleaned_data["tz"]
    check.grace = form.cleaned_data["grace"]
    check.save()

    check.assign_all_channels()

    url = reverse("hc-checks", args=[project.code])
    url += _get_referer_qs(request)  # Preserve selected tags and search
    return redirect(url)


@require_POST
@login_required
def update_name(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    form = forms.NameTagsForm(request.POST)
    if form.is_valid():
        check.name = form.cleaned_data["name"]
        check.slug = form.cleaned_data["slug"]
        check.tags = form.cleaned_data["tags"]
        check.desc = form.cleaned_data["desc"]
        check.save()

    if "/details/" in request.META.get("HTTP_REFERER", ""):
        return redirect("hc-details", code)

    url = reverse("hc-checks", args=[check.project.code])
    url += _get_referer_qs(request)  # Preserve selected tags and search
    return redirect(url)


@require_POST
@login_required
def filtering_rules(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    form = forms.FilteringRulesForm(request.POST)
    if form.is_valid():
        check.filter_subject = form.cleaned_data["filter_subject"]
        check.filter_body = form.cleaned_data["filter_body"]
        check.start_kw = form.cleaned_data["start_kw"]
        check.success_kw = form.cleaned_data["success_kw"]
        check.failure_kw = form.cleaned_data["failure_kw"]

        check.methods = form.cleaned_data["methods"]
        check.manual_resume = form.cleaned_data["manual_resume"]
        check.save()

    return redirect("hc-details", code)


@require_POST
@login_required
def update_timeout(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    kind = request.POST.get("kind")
    if kind == "simple":
        simple_form = forms.TimeoutForm(request.POST)
        if not simple_form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "simple"
        check.timeout = simple_form.cleaned_data["timeout"]
        check.grace = simple_form.cleaned_data["grace"]
    elif kind == "cron":
        cron_form = forms.CronForm(request.POST)
        if not cron_form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "cron"
        check.schedule = cron_form.cleaned_data["schedule"]
        check.tz = cron_form.cleaned_data["tz"]
        check.grace = cron_form.cleaned_data["grace"]
    elif kind == "oncalendar":
        oncalendar_form = forms.OnCalendarForm(request.POST)
        if not oncalendar_form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "oncalendar"
        check.schedule = oncalendar_form.cleaned_data["schedule"]
        check.tz = oncalendar_form.cleaned_data["tz"]
        check.grace = oncalendar_form.cleaned_data["grace"]

    check.alert_after = check.going_down_after()
    if check.status == "up":
        assert check.alert_after
        if check.alert_after < now():
            # Checks can flip from "up" to "down" state as a result of changing check's
            # schedule.  We don't want to send notifications when changing schedule
            # interactively in the web UI. So we update the `alert_after` and `status`
            # fields, and create a Flip object here the same way as `sendalerts` would
            # do, but without sending an actual alert.
            #
            # We need to create the Flip object because otherwise the calculation
            # in Check.downtimes() will come out wrong (when this check later comes up,
            # we will have no record of when it went down).
            check.create_flip("down", mark_as_processed=True)

            check.alert_after = None
            check.status = "down"

    check.save()

    if "/details/" in request.META.get("HTTP_REFERER", ""):
        return redirect("hc-details", code)

    url = reverse("hc-checks", args=[check.project.code])
    url += _get_referer_qs(request)  # Preserve selected tags and search
    return redirect(url)


@require_POST
def cron_preview(request: HttpRequest) -> HttpResponse:
    form = forms.CronPreviewForm(request.POST)
    if not form.is_valid():
        return render(request, "front/cron_preview.html", {"form": form})

    tz = form.cleaned_data["tz"]
    now_local = now().astimezone(ZoneInfo(tz))
    it = CronSim(form.cleaned_data["schedule"], now_local)
    ctx = {
        "tz": tz,
        "dates": list(islice(it, 0, 6)),
        "desc": it.explain(),
    }
    return render(request, "front/cron_preview.html", ctx)


@require_POST
@login_required
def oncalendar_preview(request: HttpRequest) -> HttpResponse:
    schedule = request.POST.get("schedule", "")
    tz = request.POST.get("tz")
    ctx: dict[str, object] = {"tz": tz, "dates": []}

    if tz not in all_timezones:
        ctx["bad_tz"] = True
        return render(request, "front/oncalendar_preview.html", ctx)

    now_local = now().astimezone(ZoneInfo(tz))
    try:
        it = OnCalendar(schedule, now_local)
        iterations = 6 if tz == "UTC" else 4
        ctx["dates"] = list(islice(it, 0, iterations))
    except OnCalendarError:
        ctx["bad_schedule"] = True

    if not ctx["dates"]:
        ctx["bad_schedule"] = True

    return render(request, "front/oncalendar_preview.html", ctx)


def validate_schedule(request: HttpRequest) -> HttpResponse:
    kind = request.GET.get("kind", "")

    validator: CronValidator | OnCalendarValidator
    if kind == "cron":
        validator = CronValidator()
    elif kind == "oncalendar":
        validator = OnCalendarValidator()
    else:
        return HttpResponseBadRequest()

    schedule = request.GET.get("schedule", "")
    try:
        validator(schedule)
        return JsonResponse({"result": True})
    except ValidationError:
        return JsonResponse({"result": False})


@login_required
def ping_details(
    request: AuthenticatedHttpRequest, code: UUID, n: int | None = None
) -> HttpResponse:
    # This view makes two non-obvious SQL queries:
    # * it calls ping.get_body(), which reads self.owner.code, triggering a query
    # * the template calls ping.duration() which queries past "/start" events

    check, rw = _get_check_for_user(request, code)
    q = Ping.objects.filter(owner=check)
    if n:
        q = q.filter(n=n)
    else:
        # When n is not specified, look up the most recent success or failure,
        # ignoring "start", "log", "ign" events
        q = q.exclude(kind__in=("start", "log", "ign"))

    try:
        ping = q.latest("created")
    except Ping.DoesNotExist:
        return render(request, "front/ping_details_not_found.html")

    body = ping.get_body()
    ctx = {
        "check": check,
        "ping": ping,
        "body": body,
        "plain": None,
        "html": None,
        "active": None,
    }

    if ping.scheme == "email" and body:
        parsed = email.message_from_string(body, policy=email.policy.SMTP)
        ctx["subject"] = parsed.get("subject", "")

        # The "active" tab is set to show the value that's successfully parsed last.
        # Per the current implementation, this means that if both plain text and HTML
        # content are present, the ping details dialog will initially display the HTML
        # content, otherwise - only one content type exists, and we default to that
        # (either plain text or HTML, at least one of them should exist in a
        # valid email).
        #
        # NOTE: If both plain text and html have not been parsed successfully the
        # "active" tab is not set at all, but currently this is not an issue since in
        # this case the "ping details" template does not render any tabs.

        plain_mime_part = parsed.get_body(("plain",))
        if plain_mime_part:
            ctx["plain"] = plain_mime_part.get_content()
            ctx["active"] = "plain"

        html_mime_part = parsed.get_body(("html",))
        if html_mime_part:
            ctx["html"] = html_mime_part.get_content()
            ctx["active"] = "html"

    return render(request, "front/ping_details.html", ctx)


@login_required
def ping_body(request: AuthenticatedHttpRequest, code: UUID, n: int) -> HttpResponse:
    check, rw = _get_check_for_user(request, code)
    ping = get_object_or_404(Ping, owner=check, n=n)

    try:
        body = ping.get_body_bytes()
    except Ping.GetBodyError:
        return HttpResponse(status=503)

    if not body:
        raise Http404("not found")

    response = HttpResponse(body, content_type="application/octet-stream")
    filename = f"{check.code}-{ping.n}"
    response["Content-Disposition"] = f'attachment; filename="{filename}.txt"'
    return response


@require_POST
@login_required
def pause(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    # Track the status change for correct downtime calculation in Check.downtimes()
    check.create_flip("paused", mark_as_processed=True)

    check.status = "paused"
    check.last_start = None
    check.alert_after = None
    check.save()

    # After pausing a check we must check if all checks are up,
    # and Profile.next_nag_date needs to be cleared out:
    check.project.update_next_nag_dates()

    # Don't redirect after an AJAX request:
    if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
        return HttpResponse()

    return redirect("hc-details", code)


@require_POST
@login_required
def resume(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)
    if check.status != "paused":
        return HttpResponseBadRequest()

    check.create_flip("new", mark_as_processed=True)

    check.status = "new"
    check.last_start = None
    check.last_ping = None
    check.alert_after = None
    check.save()

    return redirect("hc-details", code)


@require_POST
@login_required
def remove_check(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    project = check.project
    check.lock_and_delete()
    return redirect("hc-checks", project.code)


@require_POST
@login_required
def clear_events(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    check.status = "new"
    check.last_ping = None
    check.last_start = None
    check.last_duration = None
    check.has_confirmation_link = False
    check.alert_after = None
    check.save()

    check.ping_set.all().delete()
    check.notification_set.all().delete()
    check.flip_set.all().delete()

    return redirect("hc-details", code)


class PingAnnotations(TypedDict):
    body_raw_preview: bytes


def _get_events(
    check: Check,
    page_limit: int,
    start: datetime,
    end: datetime,
    kinds: tuple[str, ...] | None = None,
) -> list[Notification | WithAnnotations[Ping, PingAnnotations] | Flip]:
    # Sorting by "n" instead of "id" is important here. Both give the same
    # query results, but sorting by "id" can cause postgres to pick
    # api_ping.id index (slow if the api_ping table is big). Sorting by
    # "n" works around the problem--postgres picks the api_ping.owner_id index.
    pq = check.visible_pings.order_by("-n")
    pq = pq.filter(created__gte=start, created__lte=end)
    if kinds is not None:
        kinds_filter = Q(kind__in=kinds)
        if "success" in kinds:
            kinds_filter = kinds_filter | Q(kind__isnull=True) | Q(kind="")
        pq = pq.filter(kinds_filter)

    # Optimization: defer loading body_raw, instead load its first 150 bytes
    # as "body_raw_preview". This reduces both network I/O to database, and disk I/O
    # on the database host if the database contains large request bodies.
    pq = pq.defer("body_raw")
    pq = pq.annotate(body_raw_preview=Substr("body_raw", 1, 151))
    pings = list(pq[:page_limit])

    # Optimization: the template will access Ping.duration, which would generate a
    # SQL query per displayed ping. Since we've already fetched a list of pings,
    # for some of them we can calculate durations more efficiently, without causing
    # additional SQL queries:
    starts: dict[UUID | None, datetime | None] = {}
    num_misses = 0
    for ping in reversed(pings):
        if ping.kind == "start":
            starts[ping.rid] = ping.created
        elif ping.kind in (None, "", "fail"):
            if ping.rid not in starts:
                # We haven't seen a start, success or fail event for this rid.
                # Will need to fall back to Ping.duration().
                num_misses += 1
            else:
                ping.duration = None
                matching_start = starts[ping.rid]
                if matching_start is not None:
                    if ping.created - matching_start < MAX_DURATION:
                        ping.duration = ping.created - matching_start

            starts[ping.rid] = None

    # If we will need to fall back to Ping.duration() more than 10 times
    # then disable duration display altogether:
    if num_misses > 10:
        for ping in pings:
            ping.duration = None

    alerts: list[Notification] = []
    if kinds and "notification" in kinds:
        aq = check.notification_set.order_by("-created")
        aq = aq.filter(created__gte=start, created__lte=end, check_status="down")
        aq = aq.select_related("channel")
        alerts = list(aq[:page_limit])

    flips: list[Flip] = []
    if kinds is None or "flip" in kinds:
        fq = check.flip_set.order_by("-created")
        fq = fq.filter(created__gte=start, created__lte=end)
        flips = list(fq[:page_limit])

    events = pings + alerts + flips
    # Sort events by the timestamp.
    # If timestamps are equal, put flips chronologically after pings
    events.sort(key=lambda el: (el.created, isinstance(el, Flip)), reverse=True)
    return events[:page_limit]


@login_required
def log(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)

    smin = check.created
    smax = now()
    oldest_ping = check.visible_pings.order_by("n").first()
    if oldest_ping:
        smin = max(smin, oldest_ping.created)

    events = _get_events(check, 1000, start=smin, end=smax)
    ctx = {
        "page": "log",
        "project": check.project,
        "check": check,
        "min": smin,
        "max": smax,
        "events": events,
        "oldest_ping": oldest_ping,
    }

    if events:
        # A full precision timestamp of the most recent event.
        # This will be used client-side for fetching live updates to specify
        # "return any events after *this* point".
        ctx["last_event_timestamp"] = events[0].created.timestamp()

    return render(request, "front/log.html", ctx)


@login_required
def details(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    _refresh_last_active_date(request)
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)

    if request.GET.get("urls") in ("uuid", "slug") and rw:
        check.project.show_slugs = request.GET["urls"] == "slug"
        check.project.save()

    all_channels = check.project.channel_set.order_by("created")
    regular_channels: list[Channel] = []
    group_channels: list[Channel] = []
    for channel in all_channels:
        channels = group_channels if channel.kind == "group" else regular_channels
        channels.append(channel)

    all_tags = set()
    sibling_checks = Check.objects.filter(project=check.project).only("tags", "tz")
    for sibling in sibling_checks:
        if sibling.tags:
            all_tags.update(sibling.tags.split(" "))

    ctx = {
        "page": "details",
        "project": check.project,
        "check": check,
        "rw": rw,
        "channels": regular_channels,
        "group_channels": group_channels,
        "enabled_channels": list(check.channel_set.all()),
        "common_timezones": _common_timezones(sibling_checks),
        "timezones": all_timezones,
        "downtimes": check.downtimes(3, request.profile.tz),
        "tz": request.profile.tz,
        "is_copied": "copied" in request.GET,
        "all_tags": " ".join(sorted(all_tags)),
    }

    return render(request, "front/details.html", ctx)


@login_required
def uncloak(request: AuthenticatedHttpRequest, unique_key: str) -> HttpResponse:
    for check in request.profile.checks_from_all_projects().only("code"):
        if check.unique_key == unique_key:
            return redirect("hc-details", check.code)

    raise Http404("not found")


@login_required
def transfer(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    if request.method == "POST":
        form = forms.TransferForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        target_project = _get_rw_project_for_user(request, form.cleaned_data["project"])
        if target_project.owner_id != check.project.owner_id:
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
def copy(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    if check.project.num_checks_available() <= 0:
        return HttpResponseBadRequest()

    new_name = check.name + " (copy)"
    # Make sure we don't exceed the 100 character db field limit:
    if len(new_name) > 100:
        new_name = check.name[:90] + "... (copy)"

    new_slug = check.slug + "-copy"
    if len(new_slug) > 100:
        new_slug = ""

    copied = Check(project=check.project)
    copied.name = new_name
    copied.slug = new_slug
    copied.desc, copied.tags = check.desc, check.tags

    copied.filter_subject = check.filter_subject
    copied.filter_body = check.filter_body
    copied.start_kw = check.start_kw
    copied.success_kw = check.success_kw
    copied.failure_kw = check.failure_kw

    copied.methods = check.methods
    copied.manual_resume = check.manual_resume

    copied.kind = check.kind
    copied.timeout, copied.grace = check.timeout, check.grace
    copied.schedule, copied.tz = check.schedule, check.tz
    copied.save()

    copied.channel_set.add(*check.channel_set.all())

    url = reverse("hc-details", args=[copied.code], query={"copied": 1})
    return redirect(url)


def status_single(request: HttpRequest, code: UUID) -> HttpResponse:
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    # We now know user is logged, tell the type checker request.profile exists-
    request = cast(AuthenticatedHttpRequest, request)
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)

    status = check.get_status()
    events = _get_events(check, 30, start=check.created, end=now())
    updated = "1"
    if len(events):
        updated = str(events[0].created.timestamp())

    doc = {
        "status": status,
        "status_text": STATUS_TEXT_TMPL.render({"check": check, "rw": rw}),
        "title": down_title(check),
        "updated": updated,
        "started": check.last_start is not None,
    }

    if updated != request.GET.get("u"):
        doc["events"] = EVENTS_TMPL.render({"check": check, "events": events})
        downtimes = check.downtimes(3, request.profile.tz)
        doc["downtimes"] = DOWNTIMES_TMPL.render(
            {"downtimes": downtimes, "tz": request.profile.tz}
        )

    return JsonResponse(doc)


@login_required
def badges(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project, rw = _get_project_for_user(request, code)

    if request.method == "POST":
        form = forms.BadgeSettingsForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        fmt = form.cleaned_data["fmt"]
        states = form.cleaned_data["states"]
        with_late = True if states == "3" else False
        if form.cleaned_data["target"] == "all":
            label = settings.MASTER_BADGE_LABEL
            url = get_badge_url(project.badge_key, "*", fmt, with_late)
        elif form.cleaned_data["target"] == "tag":
            label = form.cleaned_data["tag"]
            url = get_badge_url(project.badge_key, label, fmt, with_late)
        elif form.cleaned_data["target"] == "check":
            check = project.check_set.get(code=form.cleaned_data["check"])
            url = absolute_reverse(
                "hc-badge-check", args=[states, check.badge_key, fmt]
            )
            label = check.name_then_code()

        if fmt == "shields":
            url = "https://img.shields.io/endpoint?" + urlencode({"url": url})

        ctx = {"fmt": fmt, "label": label, "url": url}
        return render(request, "front/badges_preview.html", ctx)

    checks = list(project.check_set.order_by("name"))
    tags = set()
    for check in checks:
        tags.update(check.tags_list())

    sorted_tags = sorted(tags, key=lambda s: s.lower())

    ctx = {
        "project": project,
        "page": "badges",
        "checks": checks,
        "tags": sorted_tags,
        "fmt": "svg",
        "label": settings.MASTER_BADGE_LABEL,
        "url": get_badge_url(project.badge_key, "*"),
    }
    return render(request, "front/badges.html", ctx)


@login_required
def channels(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project, rw = _get_project_for_user(request, code)

    if request.method == "POST":
        if not rw:
            return HttpResponseForbidden()

        channel_code = request.POST["channel"]
        try:
            channel = Channel.objects.get(code=channel_code)
        except Channel.DoesNotExist:
            return HttpResponseBadRequest()
        if channel.project_id != project.id:
            return HttpResponseForbidden()

        new_checks = []
        for key in request.POST:
            if key.startswith("check-"):
                check_code = key[6:]
                try:
                    check = Check.objects.get(code=check_code)
                except Check.DoesNotExist:
                    return HttpResponseBadRequest()
                if check.project_id != project.id:
                    return HttpResponseForbidden()
                new_checks.append(check)

        channel.checks.set(new_checks)
        return redirect("hc-channels", project.code)

    channels = project.channel_set.annotate(n_checks=Count("checks"))
    # Sort groups first, then in the creation order
    channels = channels.annotate(is_group=Case(When(kind="group", then=0), default=1))
    channels = channels.order_by("is_group", "created")

    ctx = {
        "page": "channels",
        "rw": rw,
        "project": project,
        "profile": project.owner_profile,
        "channels": channels,
        "enable_apprise": settings.APPRISE_ENABLED is True,
        "enable_call": bool(settings.TWILIO_AUTH),
        "enable_discord": bool(settings.DISCORD_CLIENT_ID),
        "enable_github": bool(settings.GITHUB_CLIENT_ID),
        "enable_matrix": bool(settings.MATRIX_ACCESS_TOKEN),
        "enable_mattermost": settings.MATTERMOST_ENABLED is True,
        "enable_msteams": settings.MSTEAMS_ENABLED is True,
        "enable_opsgenie": settings.OPSGENIE_ENABLED is True,
        "enable_pagertree": settings.PAGERTREE_ENABLED is True,
        "enable_pd": settings.PD_ENABLED is True,
        "enable_prometheus": settings.PROMETHEUS_ENABLED is True,
        "enable_pushbullet": bool(settings.PUSHBULLET_CLIENT_ID),
        "enable_pushover": bool(settings.PUSHOVER_API_TOKEN),
        "enable_rocketchat": settings.ROCKETCHAT_ENABLED is True,
        "enable_shell": settings.SHELL_ENABLED is True,
        "enable_signal": bool(settings.SIGNAL_CLI_SOCKET),
        "enable_slack": settings.SLACK_ENABLED is True,
        "enable_slack_btn": bool(settings.SLACK_CLIENT_ID),
        "enable_sms": bool(settings.TWILIO_AUTH),
        "enable_spike": settings.SPIKE_ENABLED is True,
        "enable_telegram": bool(settings.TELEGRAM_TOKEN),
        "enable_trello": bool(settings.TRELLO_APP_KEY),
        "enable_victorops": settings.VICTOROPS_ENABLED is True,
        "enable_webhooks": settings.WEBHOOKS_ENABLED is True,
        "enable_whatsapp": settings.TWILIO_USE_WHATSAPP,
        "enable_zulip": settings.ZULIP_ENABLED is True,
        "use_payments": settings.USE_PAYMENTS,
    }

    return render(request, "front/channels.html", ctx)


@login_required
def channel_checks(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    channel = _get_rw_channel_for_user(request, code)

    assigned = set(channel.checks.values_list("code", flat=True).distinct())
    checks = channel.project.check_set.order_by("created")
    ctx = {"checks": checks, "assigned": assigned, "channel": channel}

    return render(request, "front/channel_checks.html", ctx)


@require_POST
@login_required
def update_channel_name(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    channel = _get_rw_channel_for_user(request, code)

    form = forms.ChannelNameForm(request.POST)
    if form.is_valid():
        channel.name = form.cleaned_data["name"]
        channel.save()

    return redirect("hc-channels", channel.project.code)


@require_POST
@login_required
def send_test_notification(
    request: AuthenticatedHttpRequest, code: UUID
) -> HttpResponse:
    channel, rw = _get_channel_for_user(request, code)

    dummy = Check(name="TEST", status="down", project=channel.project)
    dummy.last_ping = now() - td(days=1)
    dummy.n_pings = 42

    dummy_flip = Flip(owner=dummy)
    dummy_flip.created = now()
    dummy_flip.old_status = "up"
    dummy_flip.new_status = "down"
    dummy_flip.reason = "timeout"

    # Delete all older test notifications for this channel
    Notification.objects.filter(channel=channel, owner=None).delete()

    # Send the test notification
    error = channel.notify(dummy_flip, is_test=True)

    if error == "no-op":
        # This channel may be configured to send "up" notifications only.
        dummy_flip.old_status = "down"
        dummy_flip.new_status = "up"
        error = channel.notify(dummy_flip, is_test=True)

    if error:
        messages.warning(request, f"Could not send a test notification. {error}.")
    else:
        messages.success(request, "Test notification sent!")

    return redirect("hc-channels", channel.project.code)


@require_POST
@login_required
def remove_channel(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    channel = _get_rw_channel_for_user(request, code)
    project = channel.project
    channel.delete()

    return redirect("hc-channels", project.code)


@login_required
def edit_channel(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    channel = _get_rw_channel_for_user(request, code)
    if channel.kind == "email":
        from hc.integrations.email.views import email_form

        return email_form(request, channel)
    elif channel.kind == "webhook":
        from hc.integrations.webhook.views import webhook_form

        return webhook_form(request, channel)
    elif channel.kind == "sms":
        from hc.integrations.sms.views import sms_form

        return sms_form(request, channel)
    elif channel.kind == "signal":
        from hc.integrations.signal.views import signal_form

        return signal_form(request, channel)
    elif channel.kind == "whatsapp":
        from hc.integrations.whatsapp.views import whatsapp_form

        return whatsapp_form(request, channel)
    elif channel.kind == "ntfy":
        from hc.integrations.ntfy.views import ntfy_form

        return ntfy_form(request, channel)
    elif channel.kind == "group":
        from hc.integrations.group.views import group_form

        return group_form(request, channel)

    return HttpResponseBadRequest()


def log_events(request: HttpRequest, code: UUID) -> HttpResponse:
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)
    form = forms.LogFiltersForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest()

    if form.cleaned_data["u"]:
        # We are live-loading more events
        start = form.cleaned_data["u"] + td(microseconds=1)
        end = now()
    else:
        # We're applying new filters
        start = check.created
        end = form.cleaned_data["end"] or now()

    # clamp start to the date of the oldest visible ping
    oldest_ping = check.visible_pings.order_by("n").first()
    if oldest_ping:
        start = max(start, oldest_ping.created)

    events = _get_events(check, 1000, start=start, end=end, kinds=form.kinds())
    response = render(request, "front/log_rows.html", {"events": events})

    if events:
        # Include a full precision timestamp of the most recent event in a
        # response header. This will be used client-side for fetching live updates
        # to specify "return any events after *this* point".
        response["X-Last-Event-Timestamp"] = str(events[0].created.timestamp())
    return response


def contact_vcf(request: HttpRequest) -> HttpResponse:
    ctx = {
        "email": settings.DEFAULT_FROM_EMAIL,
        "site_name": settings.SITE_NAME,
        "tel": settings.TWILIO_FROM,
        "site_root": settings.SITE_ROOT,
    }
    return render(request, "contact.vcf", ctx, content_type="text/vcard")


# Forks: add custom views after this line
