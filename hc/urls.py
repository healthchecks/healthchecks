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
    path(prefix, include("hc.integrations.apprise.urls")),
    path(prefix, include("hc.integrations.call.urls")),
    path(prefix, include("hc.integrations.discord.urls")),
    path(prefix, include("hc.integrations.github.urls")),
    path(prefix, include("hc.integrations.googlechat.urls")),
    path(prefix, include("hc.integrations.gotify.urls")),
    path(prefix, include("hc.integrations.group.urls")),
    path(prefix, include("hc.integrations.matrix.urls")),
    path(prefix, include("hc.integrations.mattermost.urls")),
    path(prefix, include("hc.integrations.msteamsw.urls")),
    path(prefix, include("hc.integrations.ntfy.urls")),
    path(prefix, include("hc.integrations.opsgenie.urls")),
    path(prefix, include("hc.integrations.pd.urls")),
    path(prefix, include("hc.integrations.po.urls")),
    path(prefix, include("hc.integrations.pagertree.urls")),
    path(prefix, include("hc.integrations.pushbullet.urls")),
    path(prefix, include("hc.integrations.rocketchat.urls")),
    path(prefix, include("hc.integrations.shell.urls")),
    path(prefix, include("hc.integrations.signal.urls")),
    path(prefix, include("hc.integrations.slack.urls")),
    path(prefix, include("hc.integrations.sms.urls")),
    path(prefix, include("hc.integrations.spike.urls")),
    path(prefix, include("hc.integrations.telegram.urls")),
    path(prefix, include("hc.integrations.trello.urls")),
    path(prefix, include("hc.integrations.victorops.urls")),
    path(prefix, include("hc.integrations.webhook.urls")),
    path(prefix, include("hc.integrations.whatsapp.urls")),
    path(prefix, include("hc.integrations.zulip.urls")),
]
