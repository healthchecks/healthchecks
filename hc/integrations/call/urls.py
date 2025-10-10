from __future__ import annotations

from django.urls import path
from hc.integrations.call import views

urlpatterns = [
    path("projects/<uuid:code>/add_call/", views.add, name="hc-add-call"),
]
