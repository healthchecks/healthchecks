from __future__ import annotations

from django.urls import path
from hc.integrations.signal import views

urlpatterns = [
    path("projects/<uuid:code>/add_signal/", views.add_signal, name="hc-add-signal"),
    path("signal_captcha/", views.signal_captcha, name="hc-signal-captcha"),
    path("signal_verify/", views.verify_signal_number, name="hc-signal-verify"),
]
