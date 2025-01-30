from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error, Warning, register
from django.http.request import split_domain_port, validate_host


class ApiConfig(AppConfig):
    name = "hc.api"


@register()  # W001, W002, W005, E002, E003
def settings_check(
    app_configs: Sequence[AppConfig] | None,
    databases: Sequence[str] | None,
    **kwargs: dict[str, Any],
) -> list[Error | Warning]:
    items: list[Error | Warning] = []

    site_root_parts = urlsplit(settings.SITE_ROOT)
    if not site_root_parts.scheme:
        items.append(
            Warning(
                "Invalid settings.SITE_ROOT value",
                hint="SITE_ROOT should start with either http:// or https://",
                id="hc.api.W001",
            )
        )

    host, _ = split_domain_port(site_root_parts.netloc)
    if site_root_parts.scheme and not validate_host(host, settings.ALLOWED_HOSTS):
        items.append(
            Error(
                "The hostname in settings.SITE_ROOT is not found in settings.ALLOWED_HOSTS",
                hint=f"Add '{host}' to settings.ALLOWED_HOSTS",
                id="hc.api.E002",
            )
        )

    if not settings.EMAIL_HOST:
        items.append(
            Warning(
                "settings.EMAIL_HOST is not set, cannot send email",
                hint="See https://github.com/healthchecks/healthchecks#sending-emails",
                id="hc.api.W002",
            )
        )

    v = settings.SECURE_PROXY_SSL_HEADER
    if v is not None and (not isinstance(v, tuple) or len(v) != 2):
        items.append(
            Warning(
                "settings.SECURE_PROXY_SSL_HEADER is not 2-element tuple",
                hint="See https://healthchecks.io/docs/self_hosted_configuration/#SECURE_PROXY_SSL_HEADER",
                id="hc.api.W005",
            )
        )

    if settings.TIME_ZONE != "UTC":
        items.append(
            Error(
                "settings.TIME_ZONE is not 'UTC'",
                hint="Healthchecks is designed to use UTC internally, changing this setting will break things",
                id="hc.api.E003",
            )
        )

    return items


@register()  # W003
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
                    id="hc.api.W003",
                )
            )

    return items


@register()  # W004
def apprise_installed_check(
    app_configs: Sequence[AppConfig] | None,
    databases: Sequence[str] | None,
    **kwargs: dict[str, Any],
) -> list[Warning]:
    if not settings.APPRISE_ENABLED:
        return []

    items = []
    try:
        import apprise
    except ImportError:
        items.append(
            Warning(
                "settings.APPRISE_ENABLED is set to True, but apprise is not installed",
                hint="try installing it using `pip install apprise`",
                id="hc.api.W004",
            )
        )

    return items


@register()  # E001
def mariadb_uuid_check(
    app_configs: Sequence[AppConfig] | None,
    databases: Sequence[str] | None,
    **kwargs: dict[str, Any],
) -> list[Error]:
    from django.db import connection

    if connection.vendor != "mysql":
        return []

    with connection.cursor() as cursor:
        cursor.execute(
            # Put the datatype lookup in a subquery. This is to make sure we get a
            # row back even when the "api_check" table does not exist yet.
            """
            SELECT VERSION(),
              (SELECT DATA_TYPE
               FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE()
                 AND TABLE_NAME = 'api_check'
                 AND COLUMN_NAME = 'code')
            """
        )
        version, data_type = cursor.fetchone()
        if "MariaDB" not in version:
            return []

        version_parts = version.split(".")
        major, minor = int(version_parts[0]), int(version_parts[1])

        # If:
        # - we are using MariaDB 10.7+
        # - *and* the UUID columns exist and use a varchar datatype,
        # then we have a problem.
        if major >= 10 and minor >= 7 and data_type == "char":
            e = Error(
                "Detected MariaDB >= 10.7, a manual migration to UUID datatypes required",
                hint="See https://github.com/healthchecks/healthchecks/issues/929 for details",
                id="hc.api.E001",
            )
            return [e]

    return []
