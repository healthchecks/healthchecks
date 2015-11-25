from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^pricing/$',
        views.pricing,
        name="hc-pricing"),

    url(r'^pricing/create_plan/$',
        views.create_plan,
        name="hc-create-plan"),

    url(r'^pricing/update_plan/$',
        views.update_plan,
        name="hc-update-plan"),

    url(r'^pricing/cancel_plan/$',
        views.cancel_plan,
        name="hc-cancel-plan"),

]
