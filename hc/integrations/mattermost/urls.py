from __future__ import annotations

from django.urls import path
from hc.integrations.mattermost import views

urlpatterns = [
    path("integrations/mattermost/", views.mattermost_help, name="hc-mattermost-help"),
    path("projects/<uuid:code>/add_mattermost/", views.add, name="hc-add-mattermost"),
]
