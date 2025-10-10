from __future__ import annotations

from django.urls import path
from hc.integrations.github import views

urlpatterns = [
    path("integrations/add_github/", views.select),
    path("projects/<uuid:code>/add_github/", views.add, name="hc-add-github"),
    path(
        "projects/<uuid:code>/add_github/save/", views.save, name="hc-add-github-save"
    ),
]
