from __future__ import annotations

from django.urls import path
from hc.integrations.googlechat import views

urlpatterns = [
    path("integrations/googlechat/", views.help, name="hc-googlechat-help"),
    path("projects/<uuid:code>/add_googlechat/", views.add, name="hc-add-googlechat"),
]
