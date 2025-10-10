from __future__ import annotations

from django.urls import path
from hc.integrations.email import views

urlpatterns = [
    path(
        "integrations/<uuid:code>/verify/<slug:token>/",
        views.verify,
        name="hc-verify-email",
    ),
    path(
        "integrations/<uuid:code>/unsub/<str:signed_token>/",
        views.unsubscribe,
        name="hc-unsubscribe-alerts",
    ),
    path("projects/<uuid:code>/add_email/", views.add, name="hc-add-email"),
]
