from __future__ import annotations

from urllib.parse import urlparse
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from hc.accounts import views as accounts_views

prefix = ""
if _path := urlparse(settings.SITE_ROOT).path.lstrip("/"):
    prefix = f"{_path}/"

urlpatterns = [
    path(f"{prefix}admin/login/", accounts_views.login),
    path(f"{prefix}admin/", admin.site.urls),
    path(prefix, include("hc.accounts.urls")),
    path(prefix, include("hc.api.urls")),
    path(prefix, include("hc.front.urls")),
    path(prefix, include("hc.payments.urls")),
]
