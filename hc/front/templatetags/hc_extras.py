from __future__ import annotations

import re
from datetime import timedelta as td

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.timezone import now

from hc.lib.date import format_approx_duration, format_duration, format_hms

register = template.Library()


@register.filter
def hc_duration(td):
    return format_duration(td)


@register.filter
def hc_approx_duration(td):
    return format_approx_duration(td)


@register.filter
def hms(td):
    return format_hms(td)


@register.simple_tag
def site_name():
    return settings.SITE_NAME


@register.simple_tag
def support_email():
    return settings.SUPPORT_EMAIL


@register.simple_tag
def absolute_site_logo_url():
    """Return absolute URL to site's logo.

    Uses settings.SITE_LOGO_URL if set, uses
    /static/img/logo.png as fallback.
    """
    url = settings.SITE_LOGO_URL or static("img/logo.png")
    if url.startswith("/"):
        url = settings.SITE_ROOT + url

    return url


@register.filter
def mangle_link(s):
    return mark_safe(escape(s).replace(".", "<span>.</span>"))


@register.simple_tag
def site_root():
    return settings.SITE_ROOT


@register.simple_tag
def site_hostname():
    parts = settings.SITE_ROOT.split("://")
    return parts[1]


@register.simple_tag
def site_version():
    return settings.VERSION


@register.simple_tag
def debug_warning():
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


def naturalize_int_match(match):
    n = int(match.group(0))
    return f"{n:08}"


def natural_name_key(check):
    s = check.name.lower().strip()
    return re.sub(r"\d+", naturalize_int_match, s)


def last_ping_key(check):
    return check.last_ping.isoformat() if check.last_ping else "9999"


def not_down_key(check):
    return check.get_status() != "down"


@register.filter
def sortchecks(checks, key):
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
def num_down_title(num_down):
    if num_down:
        return "%d down – %s" % (num_down, settings.SITE_NAME)
    else:
        return settings.SITE_NAME


@register.filter
def down_title(check):
    """Prepare title tag for the Details page.

    If the check is down, return "DOWN - Name - site_name".
    Otherwise, return "Name - site_name".

    """

    s = "%s – %s" % (check.name_then_code(), settings.SITE_NAME)
    if check.get_status() == "down":
        s = "DOWN – " + s

    return s


@register.filter
def break_underscore(s):
    """Add zero-width-space characters after underscores."""

    if len(s) > 30:
        s = s.replace("_", "_\u200b")

    return s


@register.filter
def format_headers(headers):
    return "\n".join("%s: %s" % (k, v) for k, v in headers.items())


@register.simple_tag
def now_isoformat():
    return now().replace(microsecond=0).isoformat()


@register.filter
def timestamp(td):
    return int(td.timestamp())


@register.filter
def guess_schedule(check):
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


FORMATTED_PING_ENDPOINT = (
    f"""<span class="base hidden-md">{settings.PING_ENDPOINT}</span>"""
)


@register.filter
def format_ping_endpoint(ping_url):
    """Wrap the ping endpoint in span tags for styling with CSS."""

    assert ping_url.startswith(settings.PING_ENDPOINT)
    tail = ping_url[len(settings.PING_ENDPOINT) :]
    return mark_safe(FORMATTED_PING_ENDPOINT + escape(tail))


@register.filter
def mask_key(key):
    return key[:4] + "*" * len(key[4:])


@register.filter
def underline(s):
    return "=" * len(str(s))


@register.filter
def first5(rid):
    return str(rid)[:5]


@register.filter
def add6days(dt):
    return dt + td(days=6)


@register.filter
def mask_phone(phone):
    if len(phone) > 7:
        return phone[:4] + "******" + phone[-3:]

    return phone


@register.simple_tag(takes_context=True)
def sort_url(context, sort):
    q = context["request"].GET.copy()
    q["sort"] = sort
    return mark_safe("?" + q.urlencode())
