from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^pricing/$',
        views.pricing,
        name="hc-pricing"),

    url(r'^accounts/profile/billing/$',
        views.billing,
        name="hc-billing"),

    url(r'^accounts/profile/billing/history/$',
        views.billing_history,
        name="hc-billing-history"),

    url(r'^accounts/profile/billing/address/$',
        views.address,
        name="hc-billing-address"),

    url(r'^accounts/profile/billing/payment_method/$',
        views.payment_method,
        name="hc-payment-method"),

    url(r'^invoice/pdf/([\w-]+)/$',
        views.pdf_invoice,
        name="hc-invoice-pdf"),

    url(r'^pricing/set_plan/$',
        views.set_plan,
        name="hc-set-plan"),

    url(r'^pricing/get_client_token/$',
        views.get_client_token,
        name="hc-get-client-token"),

    url(r'^pricing/charge/$', views.charge_webhook),
]
