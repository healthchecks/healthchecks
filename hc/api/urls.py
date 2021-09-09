from urllib.parse import quote, unquote

from django.urls import include, path, register_converter
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

uuid_urls = [
    path("", views.ping, name="hc-ping"),
    path("fail", views.ping, {"action": "fail"}),
    path("start", views.ping, {"action": "start"}),
    path("<int:exitstatus>", views.ping),
]

slug_urls = [
    path("fail", views.ping_by_slug, {"action": "fail"}),
    path("start", views.ping_by_slug, {"action": "start"}),
    path("<int:exitstatus>", views.ping_by_slug),
]

urlpatterns = [
    path("ping/<uuid:code>", views.ping),
    path("ping/<uuid:code>/", include(uuid_urls)),
    path("ping/<slug:ping_key>/<slug:slug>", views.ping_by_slug),
    path("ping/<slug:ping_key>/<slug:slug>/", include(slug_urls)),
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
    path("api/v1/badges/", views.badges),
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
