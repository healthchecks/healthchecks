from __future__ import annotations

from django.urls import path
from hc.integrations.trello import views

urlpatterns = [
    path(
        "integrations/add_trello/settings/",
        views.trello_settings,
        name="hc-trello-settings",
    ),
    path("projects/<uuid:code>/add_trello/", views.add, name="hc-add-trello"),
]
