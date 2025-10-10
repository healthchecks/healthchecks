from __future__ import annotations

from django.urls import path
from hc.integrations.pagertree import views

urlpatterns = [
    path("projects/<uuid:code>/add_pagertree/", views.add, name="hc-add-pagertree"),
]
