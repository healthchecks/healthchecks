from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("projects/<uuid:code>/pricing/", views.pricing, name="hc-p-pricing"),
    path("pricing/", views.pricing, name="hc-pricing"),
    path("accounts/profile/billing/", views.billing, name="hc-billing"),
    path(
        "accounts/profile/billing/history/",
        views.billing_history,
        name="hc-billing-history",
    ),
    path("accounts/profile/billing/address/", views.address, name="hc-billing-address"),
    path(
        "accounts/profile/billing/payment_method/",
        views.payment_method,
        name="hc-payment-method",
    ),
    path("pricing/update/", views.update, name="hc-update-subscription"),
    path("pricing/token/", views.token, name="hc-get-client-token"),
]
