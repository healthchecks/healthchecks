from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/',    include(admin.site.urls)),
    url(r'^accounts/', include('hc.accounts.urls')),
    url(r'^',          include('hc.checks.urls')),
    url(r'^',          include('hc.front.urls')),
]
