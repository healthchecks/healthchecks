from django.contrib import admin
from django.urls import include, path

from hc.accounts import views as accounts_views

urlpatterns = [
    path('admin/login/', accounts_views.login),
    path('admin/', admin.site.urls),
    path('accounts/', include('hc.accounts.urls')),
    path('projects/<uuid:code>/settings/', accounts_views.project, name="hc-project-settings"),
    path('', include('hc.api.urls')),
    path('', include('hc.front.urls')),
    path('', include('hc.payments.urls'))
]
