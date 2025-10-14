from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Warning, register


class WhatsappConfig(AppConfig):
    name = "hc.integrations.whatsapp"


@register()
def whatsapp_settings_check(
    app_configs: Sequence[AppConfig] | None,
    databases: Sequence[str] | None,
    **kwargs: dict[str, Any],
) -> list[Warning]:
    if not settings.TWILIO_USE_WHATSAPP:
        return []

    items = []
    for key in (
        "TWILIO_ACCOUNT",
        "TWILIO_AUTH",
        "TWILIO_FROM",
        "TWILIO_MESSAGING_SERVICE_SID",
        "WHATSAPP_DOWN_CONTENT_SID",
        "WHATSAPP_UP_CONTENT_SID",
    ):
        if not getattr(settings, key):
            items.append(
                Warning(
                    f"The WhatsApp integration requires the settings.{key} to be set",
                    hint=f"See https://healthchecks.io/docs/self_hosted_configuration/#{key}",
                    id="hc.integrations.whatsapp.W001",
                )
            )

    return items
