from __future__ import annotations

from django.urls import path
from hc.integrations.matrix import views

urlpatterns = [
    path("projects/<uuid:code>/add_matrix/", views.add, name="hc-add-matrix"),
]
