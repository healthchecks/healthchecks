from __future__ import annotations

from django.urls import path
from hc.integrations.msteamsw import views

urlpatterns = [
    path("projects/<uuid:code>/add_msteams/", views.add_msteams, name="hc-add-msteams"),
]
