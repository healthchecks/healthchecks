from __future__ import annotations

from django.urls import path

from hc.integrations.gotify import views

urlpatterns = [
    path("projects/<uuid:code>/add_gotify/", views.add, name="hc-add-gotify"),
]
