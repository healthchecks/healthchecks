from __future__ import annotations

from django.urls import path
from hc.integrations.shell import views

urlpatterns = [
    path("projects/<uuid:code>/add_shell/", views.add, name="hc-add-shell"),
]
