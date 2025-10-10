from __future__ import annotations

from django.urls import path
from hc.integrations.spike import views

urlpatterns = [
    path("projects/<uuid:code>/add_spike/", views.add_spike, name="hc-add-spike"),
]
