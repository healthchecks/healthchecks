from __future__ import annotations

from django.urls import path
from hc.integrations.whatsapp import views

urlpatterns = [
    path("projects/<uuid:code>/add_whatsapp/", views.add, name="hc-add-whatsapp"),
]
