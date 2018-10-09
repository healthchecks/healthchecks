from django.contrib import admin
from django.urls import include, path

from hc.accounts.views import login as hc_login

urlpatterns = [
    path('admin/login/', hc_login),
    path('admin/', admin.site.urls),
    path('accounts/', include('hc.accounts.urls')),
    path('', include('hc.api.urls')),
    path('', include('hc.front.urls')),
    path('', include('hc.payments.urls'))
]
