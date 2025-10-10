from __future__ import annotations

from django.urls import path
from hc.integrations.po import views

urlpatterns = [
    path("integrations/add_pushover/", views.pushover_help, name="hc-pushover-help"),
    path("projects/<uuid:code>/add_pushover/", views.add, name="hc-add-pushover"),
]
