import re

from django import template
from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe

from hc.lib.date import format_duration

register = template.Library()


@register.filter
def hc_duration(td):
    return format_duration(td)


@register.simple_tag
def site_name():
    return settings.SITE_NAME


@register.simple_tag
def escaped_site_name():
    return mark_safe(settings.SITE_NAME.replace(".", "<span>.</span>"))


@register.filter
def mangle_link(s):
    return mark_safe(escape(s).replace(".", "<span>.</span>"))


@register.simple_tag
def site_root():
    return settings.SITE_ROOT


def naturalize_int_match(match):
    return '%08d' % (int(match.group(0)),)


def natural_name_key(check):
    s = check.name.lower().strip()
    return re.sub(r'\d+', naturalize_int_match, s)


def last_ping_key(check):
    return check.last_ping.isoformat() if check.last_ping else "9999"


@register.filter
def sortchecks(checks, key):
    if key == "created":
        checks.sort(key=lambda check: check.created)
    elif key.endswith("name"):
        checks.sort(key=natural_name_key, reverse=key.startswith("-"))
    elif key.endswith("last_ping"):
        checks.sort(key=last_ping_key, reverse=key.startswith("-"))

    return checks
