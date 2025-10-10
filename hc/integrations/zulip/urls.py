from __future__ import annotations

from django.urls import path
from hc.integrations.zulip import views

urlpatterns = [
    path("projects/<uuid:code>/add_zulip/", views.add, name="hc-add-zulip"),
]
