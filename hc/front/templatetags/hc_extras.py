from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from hc.lib.date import format_duration

register = template.Library()


@register.filter
def hc_duration(td):
    return format_duration(td)


@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.simple_tag
def site_name():
    return settings.SITE_NAME


@register.simple_tag
def escaped_site_name():
    return mark_safe(settings.SITE_NAME.replace(".", "<span>.</span>"))


@register.simple_tag
def site_root():
    return settings.SITE_ROOT
