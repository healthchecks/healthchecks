from __future__ import annotations

from django.urls import path
from hc.integrations.prometheus import views

urlpatterns = [
    path(
        "projects/<uuid:code>/add_prometheus/",
        views.add_prometheus,
        name="hc-add-prometheus",
    ),
    path(
        "projects/<uuid:code>/checks/metrics/<slug:key>",
        views.metrics,
    ),
    path(
        "projects/<uuid:code>/metrics/<slug:key>",
        views.metrics,
        name="hc-metrics",
    ),
    path("projects/<uuid:code>/metrics/", views.metrics, name="hc-auth-metrics"),
]
