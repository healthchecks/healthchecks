from __future__ import annotations

from django.urls import path
from hc.integrations.group import views

urlpatterns = [
    path("projects/<uuid:code>/add_group/", views.add, name="hc-add-group"),
]
