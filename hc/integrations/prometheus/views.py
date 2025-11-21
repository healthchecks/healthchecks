from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse
from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.accounts.models import Project
from hc.api.models import Check
from hc.front.decorators import require_setting
from hc.front.views import _get_project_for_user


@require_setting("PROMETHEUS_ENABLED")
@login_required
def add_prometheus(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project, rw = _get_project_for_user(request, code)
    ctx = {
        "page": "channels",
        "project": project,
        "site_scheme": urlparse(settings.SITE_ROOT).scheme,
    }
    return render(request, "add_prometheus.html", ctx)


@require_setting("PROMETHEUS_ENABLED")
def metrics(request: HttpRequest, code: UUID, key: str | None = None) -> HttpResponse:
    if key is None:
        # If key was not in the URL, expect it in the Authorization request header
        key = request.META.get("HTTP_AUTHORIZATION", "")
        if not key.startswith("Bearer "):
            return HttpResponse(status=401)

        key = key.lstrip("Bearer ")

    if len(key) != 32:
        return HttpResponseBadRequest()

    project = Project.objects.for_api_key(key, accept_rw=False, accept_ro=True)
    if project is None:
        return HttpResponseForbidden()

    checks = Check.objects.filter(project_id=project.id).order_by("id")

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def output(checks: QuerySet[Check]) -> Iterable[str]:
        labels_status_started = []
        for check in checks:
            labels = f'{{name="{esc(check.name)}", tags="{esc(check.tags)}", unique_key="{check.unique_key}"}}'
            started = 1 if check.last_start else 0
            labels_status_started.append((labels, check.get_status(), started))

        yield "# HELP hc_check_up Whether the check is currently up (1 for yes, 0 for no).\n"
        yield "# TYPE hc_check_up gauge\n"
        for labels, status, started in labels_status_started:
            value = 0 if status == "down" else 1
            yield f"hc_check_up{labels} {value}\n"

        yield "\n"
        yield "# HELP hc_check_started Whether the check is currently started (1 for yes, 0 for no).\n"
        yield "# TYPE hc_check_started gauge\n"
        for labels, status, started in labels_status_started:
            yield f"hc_check_started{labels} {started}\n"

        yield "\n"
        yield "# HELP hc_check_grace Whether the check is currently in the grace period (1 for yes, 0 for no).\n"
        yield "# TYPE hc_check_grace gauge\n"
        for labels, status, started in labels_status_started:
            value = 1 if status == "grace" else 0
            yield f"hc_check_grace{labels} {value}\n"

        yield "\n"
        yield "# HELP hc_check_paused Whether the check is currently paused (1 for yes, 0 for no).\n"
        yield "# TYPE hc_check_paused gauge\n"
        for labels, status, started in labels_status_started:
            value = 1 if status == "paused" else 0
            yield f"hc_check_paused{labels} {value}\n"

        all_tags, down_tags, num_down = set(), set(), 0
        for check, (_, status, _) in zip(checks, labels_status_started):
            all_tags.update(check.tags_list())
            if status == "down":
                num_down += 1
                down_tags.update(check.tags_list())

        yield "\n"
        yield "# HELP hc_tag_up Whether all checks with this tag are up (1 for yes, 0 for no).\n"
        yield "# TYPE hc_tag_up gauge\n"
        TMPL = """hc_tag_up{tag="%s"} %d\n"""
        for tag in sorted(all_tags):
            value = 0 if tag in down_tags else 1
            yield TMPL % (esc(tag), value)

        yield "\n"
        yield "# HELP hc_checks_total The total number of checks.\n"
        yield "# TYPE hc_checks_total gauge\n"
        yield f"hc_checks_total {len(checks)}\n"
        yield "\n"

        yield "# HELP hc_checks_down_total The number of checks currently down.\n"
        yield "# TYPE hc_checks_down_total gauge\n"
        yield f"hc_checks_down_total {num_down}\n"

    return HttpResponse(output(checks), content_type="text/plain")
