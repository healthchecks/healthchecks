from django.conf.urls import url

from hc.front import views

urlpatterns = [
    url(r'^checks/$', views.checks, name="hc-checks"),
]
