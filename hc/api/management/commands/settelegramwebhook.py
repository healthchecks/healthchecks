from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse

from hc.lib import curl

SETWEBHOOK_TMPL = "https://api.telegram.org/bot%s/setWebhook"


class Command(BaseCommand):
    help = "Set up telegram bot's webhook address"

    def handle(self, **options: Any) -> str:
        if settings.TELEGRAM_TOKEN is None:
            return "Abort: settings.TELEGRAM_TOKEN is not set"

        form = {
            "url": settings.SITE_ROOT + reverse("hc-telegram-webhook"),
            "allowed_updates": ["message", "channel_post"],
        }

        url = SETWEBHOOK_TMPL % settings.TELEGRAM_TOKEN
        r = curl.post(url, json=form)

        if r.status_code != 200:
            return "Fail: status=%d, %s" % (r.status_code, r.content.decode())

        return "Done, Telegram's webhook set to: %s" % form["url"]
