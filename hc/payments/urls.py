from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^pricing/$',
        views.pricing,
        name="hc-pricing"),

    url(r'^create_subscription/$',
        views.create,
        name="hc-create-subscription"),

    url(r'^subscription_status/$',
        views.status,
        name="hc-subscription-status"),

]
