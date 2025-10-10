from __future__ import annotations

from django.urls import path
from hc.integrations.slack import views

urlpatterns = [
    path("integrations/add_slack/", views.slack_help, name="hc-slack-help"),
    path("integrations/add_slack_btn/", views.add_complete),
    path("projects/<uuid:code>/add_slack/", views.add, name="hc-add-slack"),
    path("projects/<uuid:code>/add_slack_btn/", views.add_btn, name="hc-add-slack-btn"),
]
