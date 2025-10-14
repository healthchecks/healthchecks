from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Warning, register


class AppriseConfig(AppConfig):
    name = "hc.integrations.apprise"


@register()
def apprise_installed_check(
    app_configs: Sequence[AppConfig] | None,
    databases: Sequence[str] | None,
    **kwargs: dict[str, Any],
) -> list[Warning]:
    if not settings.APPRISE_ENABLED:
        return []

    items = []
    try:
        import apprise  # noqa
    except ImportError:
        items.append(
            Warning(
                "settings.APPRISE_ENABLED is set to True, but apprise is not installed",
                hint="try installing it using `pip install apprise`",
                id="hc.integrations.apprise.W001",
            )
        )

    return items
