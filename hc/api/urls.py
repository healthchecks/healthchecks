from urllib.parse import quote, unquote

from django.urls import path, register_converter
from hc.api import views


class QuoteConverter:
    regex = r"[\w%~_.-]+"

    def to_python(self, value):
        return unquote(value)

    def to_url(self, value):
        return quote(value, safe="")


class SHA1Converter:
    regex = "[A-z0-9]{40}"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(QuoteConverter, "quoted")
register_converter(SHA1Converter, "sha1")

urlpatterns = [
    path("ping/<uuid:code>/", views.ping, name="hc-ping-slash"),
    path("ping/<uuid:code>", views.ping, name="hc-ping"),
    path("ping/<uuid:code>/fail", views.ping, {"action": "fail"}, name="hc-fail"),
    path("ping/<uuid:code>/start", views.ping, {"action": "start"}, name="hc-start"),
    path("ping/<uuid:code>/<int:exitstatus>", views.ping),
    path("api/v1/checks/", views.checks),
    path("api/v1/checks/<uuid:code>", views.single, name="hc-api-single"),
    path("api/v1/checks/<sha1:unique_key>", views.get_check_by_unique_key),
    path("api/v1/checks/<uuid:code>/pause", views.pause, name="hc-api-pause"),
    path(
        "api/v1/notifications/<uuid:code>/status",
        views.notification_status,
        name="hc-api-notification-status",
    ),
    path("api/v1/checks/<uuid:code>/pings/", views.pings, name="hc-api-pings"),
    path("api/v1/checks/<uuid:code>/flips/", views.flips_by_uuid, name="hc-api-flips"),
    path("api/v1/checks/<sha1:unique_key>/flips/", views.flips_by_unique_key),
    path("api/v1/channels/", views.channels),
    path(
        "badge/<slug:badge_key>/<slug:signature>/<quoted:tag>.<slug:fmt>",
        views.badge,
        name="hc-badge",
    ),
    path(
        "badge/<slug:badge_key>/<slug:signature>.<slug:fmt>",
        views.badge,
        {"tag": "*"},
        name="hc-badge-all",
    ),
    path("api/v1/metrics/", views.metrics),
    path("api/v1/status/", views.status),
]
