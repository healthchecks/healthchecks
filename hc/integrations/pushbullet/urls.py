from __future__ import annotations

from django.urls import path
from hc.integrations.pushbullet import views

urlpatterns = [
    path("integrations/add_pushbullet/", views.add_complete),
    path("projects/<uuid:code>/add_pushbullet/", views.add, name="hc-add-pushbullet"),
]
