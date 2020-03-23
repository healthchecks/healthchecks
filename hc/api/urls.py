from urllib.parse import quote, unquote

from django.urls import path, register_converter
from hc.api import views


class QuoteConverter:
    regex = "[\w%~_.-]+"

    def to_python(self, value):
        return unquote(value)

    def to_url(self, value):
        return quote(value, safe="")


register_converter(QuoteConverter, "quoted")

urlpatterns = [
    path("ping/<uuid:code>/", views.ping, name="hc-ping-slash"),
    path("ping/<uuid:code>", views.ping, name="hc-ping"),
    path("ping/<uuid:code>/fail", views.ping, {"action": "fail"}, name="hc-fail"),
    path("ping/<uuid:code>/start", views.ping, {"action": "start"}, name="hc-start"),
    path("api/v1/checks/", views.checks),
    path("api/v1/checks/<uuid:code>", views.single, name="hc-api-single"),
    path("api/v1/checks/<uuid:code>/pause", views.pause, name="hc-api-pause"),
    path("api/v1/notifications/<uuid:code>/bounce", views.bounce, name="hc-api-bounce"),
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
    path("api/v1/status/", views.status),
]
