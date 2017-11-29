from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^pricing/$',
        views.pricing,
        name="hc-pricing"),

    url(r'^billing/$',
        views.billing,
        name="hc-billing"),

    url(r'^invoice/([\w-]+)/$',
        views.invoice,
        name="hc-invoice"),

    url(r'^invoice/pdf/([\w-]+)/$',
        views.pdf_invoice,
        name="hc-invoice-pdf"),

    url(r'^pricing/create_plan/$',
        views.create_plan,
        name="hc-create-plan"),

    url(r'^pricing/update_payment_method/$',
        views.update_payment_method,
        name="hc-update-payment-method"),

    url(r'^pricing/cancel_plan/$',
        views.cancel_plan,
        name="hc-cancel-plan"),

    url(r'^pricing/get_client_token/$',
        views.get_client_token,
        name="hc-get-client-token"),

]
