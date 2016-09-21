from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.contrib.staticfiles import views

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('hc.accounts.urls')),
    url(r'^', include('hc.api.urls')),
    url(r'^', include('hc.front.urls')),
    url(r'^', include('hc.payments.urls'))
]

urlpatterns += [
	url(r'^static/(?P<path>.*)$', views.serve),
]