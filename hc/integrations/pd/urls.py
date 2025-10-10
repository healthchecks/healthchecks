from __future__ import annotations

from django.urls import path
from hc.integrations.pd import views

urlpatterns = [
    path("integrations/add_pagerduty/", views.add_complete, name="hc-add-pd-complete"),
    path("integrations/pagerduty/", views.pd_help, name="hc-pagerduty-help"),
    path("projects/<uuid:code>/add_pd/", views.add, name="hc-add-pd"),
]
