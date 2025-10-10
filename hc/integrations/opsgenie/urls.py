from __future__ import annotations

from django.urls import path
from hc.integrations.opsgenie import views

urlpatterns = [
    path("projects/<uuid:code>/add_opsgenie/", views.add, name="hc-add-opsgenie"),
]
