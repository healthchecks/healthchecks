from django.conf.urls import url

from hc.api import views

urlpatterns = [
    url(r'^ping/([\w-]+)/$', views.ping, name="hc-ping"),
    url(r'^ping/([\w-]+)$', views.ping, name="hc-ping"),
    url(r'^status/([\w-]+)/$', views.status, name="hc-status"),
]
