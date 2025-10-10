from __future__ import annotations

from django.urls import path
from hc.integrations.webhook import views

urlpatterns = [
    path("projects/<uuid:code>/add_webhook/", views.add, name="hc-add-webhook"),
]
