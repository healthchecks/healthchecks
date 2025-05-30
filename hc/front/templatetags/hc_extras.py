from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import UUID

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import escape, format_html
from django.utils.safestring import SafeString, mark_safe
from django.utils.timezone import now

from hc.lib.date import format_approx_duration, format_duration, format_hms
from hc.lib.urls import absolute_url

if TYPE_CHECKING:
    from hc.api.models import Check


register = template.Library()


@register.filter
def hc_duration(d: timedelta) -> str:
    return format_duration(d)


@register.filter
def hc_approx_duration(d: timedelta) -> str:
    return format_approx_duration(d)


@register.filter
def hms(d: datetime | timedelta) -> str:
    if isinstance(d, datetime):
        return format_hms(now() - d)

    return format_hms(d)


@register.simple_tag
def site_name() -> str:
    return settings.SITE_NAME


@register.simple_tag
def support_email() -> str | None:
    return settings.SUPPORT_EMAIL


@register.simple_tag
def absolute_site_logo_url() -> str:
    """Return absolute URL to site's logo.

    Uses settings.SITE_LOGO_URL if set, uses
    /static/img/logo.png as fallback.
    """
    url = settings.SITE_LOGO_URL or static("img/logo.png")
    if url.startswith("/"):
        url = absolute_url(url)

    return url


@register.filter
def mangle_link(s: str) -> SafeString:
    return mark_safe(escape(s).replace(".", "<span>.</span>"))


@register.simple_tag
def site_root() -> str:
    return settings.SITE_ROOT


@register.simple_tag
def site_hostname() -> str:
    return urlparse(settings.SITE_ROOT).netloc


@register.simple_tag
def site_version() -> str:
    return settings.VERSION


@register.simple_tag
def debug_warning() -> str:
    if settings.DEBUG:
        return mark_safe(
            """
            <div id="debug-warning">
            Running in debug mode, do not use in production.
            </div>
        """
        )

    if settings.SECRET_KEY == "---":
        return mark_safe(
            """
            <div id="debug-warning">
            Running with an insecure SECRET_KEY value, do not use in production.
            </div>
        """
        )

    return ""


def naturalize_int_match(match: re.Match[str]) -> str:
    n = int(match.group(0))
    return f"{n:08}"


def natural_name_key(check: Check) -> str:
    s = check.name.lower().strip()
    return re.sub(r"\d+", naturalize_int_match, s)


def last_ping_key(check: Check) -> str:
    return check.last_ping.isoformat() if check.last_ping else "9999"


def not_down_key(check: Check) -> bool:
    return check.cached_status != "down"


@register.filter
def sortchecks(checks: list[Check], key: str) -> list[Check]:
    """Sort the list of checks in-place by given key, then by status=down."""

    if key == "created":
        checks.sort(key=lambda check: check.created)
    elif key.endswith("name"):
        checks.sort(key=natural_name_key, reverse=key.startswith("-"))
    elif key.endswith("last_ping"):
        checks.sort(key=last_ping_key, reverse=key.startswith("-"))

    # Move failed checks to the beginning. Sorts in python are stable
    # so this does not mess up the previous sort.
    checks.sort(key=not_down_key)

    return checks


@register.filter
def num_down_title(num_down: int) -> str:
    if num_down:
        return "%d down – %s" % (num_down, settings.SITE_NAME)
    else:
        return settings.SITE_NAME


@register.filter
def down_title(check: Check) -> str:
    """Prepare title tag for the Details page.

    If the check is down, return "DOWN - Name - site_name".
    Otherwise, return "Name - site_name".

    """

    s = "%s – %s" % (check.name_then_code(), settings.SITE_NAME)
    if check.get_status() == "down":
        s = "DOWN – " + s

    return s


@register.filter
def break_underscore(s: str) -> str:
    """Add zero-width-space characters after underscores."""

    if len(s) > 30:
        s = s.replace("_", "_\u200b")

    return s


@register.filter
def format_headers(headers: dict[str, str]) -> str:
    return "\n".join("%s: %s" % (k, v) for k, v in headers.items())


@register.simple_tag
def now_isoformat() -> str:
    return now().replace(microsecond=0).isoformat()


@register.filter
def timestamp(dt: datetime) -> int:
    return int(dt.timestamp())


@register.filter
def guess_schedule(check: Check) -> str | None:
    if check.kind == "cron":
        return check.schedule

    v = int(check.timeout.total_seconds())

    # every minute
    if v == 60:
        return "* * * * *"

    # every hour
    if v == 3600:
        return "0 * * * *"

    # every day
    if v == 3600 * 24:
        return "0 0 * * *"

    # every X minutes, if 60 is divisible by X
    minutes, seconds = divmod(v, 60)
    if minutes in (2, 3, 4, 5, 6, 10, 12, 15, 20, 30) and seconds == 0:
        return f"*/{minutes} * * * *"

    # every X hours, if 24 is divisible by X
    hours, seconds = divmod(v, 3600)
    if hours in (2, 3, 4, 6, 8, 12) and seconds == 0:
        return f"0 */{hours} * * *"

    return None


FORMATTED_PING_ENDPOINT_TMPL = (
    f"""<span class="base">{settings.PING_ENDPOINT}</span>{{}}"""
)


@register.filter
def format_ping_endpoint(ping_url: str) -> SafeString:
    """Wrap the ping endpoint in span tags for styling with CSS."""

    assert ping_url.startswith(settings.PING_ENDPOINT)
    tail = ping_url.removeprefix(settings.PING_ENDPOINT)
    return format_html(FORMATTED_PING_ENDPOINT_TMPL, tail)


@register.filter
def mask_key(key: str) -> str:
    return key[:4] + "*" * len(key[4:])


@register.filter
def underline(s: str) -> str:
    return "=" * len(str(s))


@register.filter
def first5(rid: UUID) -> str:
    return str(rid)[:5]


@register.filter
def add6days(dt: datetime) -> datetime:
    return dt + timedelta(days=6)


@register.filter
def mask_phone(phone: str) -> str:
    if len(phone) > 7:
        return phone[:4] + "******" + phone[-3:]

    return phone


@register.simple_tag(takes_context=True)
def sort_url(context: dict[str, Any], sort: str) -> SafeString:
    q = context["request"].GET.copy()
    q["sort"] = sort
    urlencoded = q.urlencode()
    assert isinstance(urlencoded, str)
    return mark_safe("?" + urlencoded)


@register.filter
def fix_asterisks(s: str) -> str:
    """Prepend asterisks with "Combining Grapheme Joiner" characters."""

    return s.replace("*", "\u034f*")


@register.filter
def pct(v: float) -> str:
    return str(int(v * 10000) / 100)


@register.filter
def decode(v: bytes) -> str:
    return bytes(v).decode(errors="replace")


@register.inclusion_tag('front/timezone_format_buttons.html')
def timezone_format_buttons(check):
    """
    Generate time zone format buttons with client-side deduplication.
    
    Deduplicate time zone buttons based on  current offsets with priority: check's tz > UTC > browser's time zone.
    """
    from datetime import datetime
    import zoneinfo
    
    now_ = datetime.now()
    buttons = []
    
    # Calculate check's time zone offset if it's a cron/oncalendar check
    check_offset_minutes = 0
    if check.kind in ("cron", "oncalendar"):
        try:
            tz = zoneinfo.ZoneInfo(check.tz)
            current_time = now_.replace(tzinfo=tz)
            offset = current_time.utcoffset()
            check_offset_minutes = int(offset.total_seconds() / 60) if offset else 0
        except Exception:
            check_offset_minutes = 0
    
    # Generate buttons in display order: UTC, Check's time zone, Browser's time zone
    
    # Add UTC first if check is simple or check's time zone isn't UTC
    if check.kind == "simple" or check.tz != "UTC":
        buttons.append({
            'name': 'UTC',
            'display_name': mark_safe('UTC'), 
            'data_format': 'UTC',
            'is_default': check.kind == "simple",
            'type': 'utc',
            'priority': 2,
            'current_offset_minutes': 0  # UTC is always 0 offset
        })
    
    # Add check's time zone second if it's a cron/oncalendar check
    if check.kind in ("cron", "oncalendar"):
        buttons.append({
            'name': check.tz,
            'display_name': mark_safe(check.tz),
            'data_format': check.tz,
            'is_default': True,
            'type': 'check',
            'priority': 1,
            'current_offset_minutes': check_offset_minutes
        })
    
    # Always add browser time zone last
    buttons.append({
        'name': 'Browser',
        'display_name': mark_safe("Browser's time zone"),
        'data_format': 'local',
        'is_default': False,
        'type': 'browser',
        'priority': 3
        # No offset - will be calculated client-side
    })
    
    return {
        'buttons': buttons, 
        'check': check
    }
