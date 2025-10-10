from __future__ import annotations

from django.urls import path
from hc.integrations.sms import views

urlpatterns = [
    path("projects/<uuid:code>/add_sms/", views.add, name="hc-add-sms"),
]
