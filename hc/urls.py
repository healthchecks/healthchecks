from django.conf.urls import include, url
from django.contrib import admin

from hc.accounts.views import login as hc_login

urlpatterns = [
    url(r'^admin/login/', hc_login, {"show_password": True}),
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/', include('hc.accounts.urls')),
    url(r'^', include('hc.api.urls')),
    url(r'^', include('hc.front.urls')),
    url(r'^', include('hc.payments.urls'))
]
