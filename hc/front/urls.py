from django.conf.urls import url

from hc.front import views

urlpatterns = [
    url(r'^$',        views.index,  name="hc-index"),
    url(r'^checks/$', views.checks, name="hc-checks"),
]
