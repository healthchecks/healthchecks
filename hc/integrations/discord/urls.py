from __future__ import annotations

from django.urls import path
from hc.integrations.discord import views

urlpatterns = [
    path("integrations/add_discord/", views.add_complete),
    path("projects/<uuid:code>/add_discord/", views.add, name="hc-add-discord"),
]
