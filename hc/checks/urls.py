from django.conf.urls import url

from hc.checks import views

urlpatterns = [
    url(r'^ping/([\w-]+)/$', views.ping, name="hc-ping"),
]
