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
    path(f"{prefix}accounts/", include("hc.accounts.urls")),
    path(f"{prefix}projects/add/", accounts_views.add_project, name="hc-add-project"),
    path(
        f"{prefix}projects/<uuid:code>/settings/",
        accounts_views.project,
        name="hc-project-settings",
    ),
    path(
        f"{prefix}projects/<uuid:code>/remove/",
        accounts_views.remove_project,
        name="hc-remove-project",
    ),
    path(prefix, include("hc.api.urls")),
    path(prefix, include("hc.front.urls")),
    path(prefix, include("hc.payments.urls")),
]
