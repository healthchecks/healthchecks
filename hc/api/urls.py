from django.conf.urls import url

from hc.api import views

urlpatterns = [
    url(r'^ping/([\w-]+)/$', views.ping, name="hc-ping-slash"),
    url(r'^ping/([\w-]+)$', views.ping, name="hc-ping"),
    url(r'^handle_email/$', views.handle_email, name="hc-handle-email"),
    url(r'^api/v1/checks/$', views.create_check),
]
