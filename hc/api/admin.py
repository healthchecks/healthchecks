from django.contrib import admin
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Count
from django.utils.safestring import mark_safe
from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.lib.date import format_duration


@admin.register(Check)
class ChecksAdmin(admin.ModelAdmin):

    class Media:
        css = {
            'all': ('css/admin/checks.css',)
        }

    search_fields = ["name", "user__email", "code"]
    list_display = ("id", "name_tags", "created", "code", "timeout_schedule",
                    "status", "email", "last_start", "last_ping", "n_pings")
    list_select_related = ("user", )
    list_filter = ("status", "kind", "last_ping",
                   "last_start")

    actions = ["send_alert"]

    def email(self, obj):
        return obj.user.email if obj.user else None

    def name_tags(self, obj):
        if not obj.tags:
            return obj.name

        return "%s [%s]" % (obj.name, obj.tags)

    def timeout_schedule(self, obj):
        if obj.kind == "simple":
            return format_duration(obj.timeout)
        elif obj.kind == "cron":
            return obj.schedule
        else:
            return "Unknown"

    timeout_schedule.short_description = "Schedule"

    def send_alert(self, request, qs):
        for check in qs:
            check.send_alert()

        self.message_user(request, "%d alert(s) sent" % qs.count())

    send_alert.short_description = "Send Alert"


class SchemeListFilter(admin.SimpleListFilter):
    title = "Scheme"
    parameter_name = 'scheme'

    def lookups(self, request, model_admin):
        return (
            ('http', "HTTP"),
            ('https', "HTTPS"),
            ('email', "Email"),
        )

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.filter(scheme=self.value())
        return queryset


class MethodListFilter(admin.SimpleListFilter):
    title = "Method"
    parameter_name = 'method'
    methods = ["HEAD", "GET", "POST", "PUT", "DELETE"]

    def lookups(self, request, model_admin):
        return zip(self.methods, self.methods)

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.filter(method=self.value())
        return queryset


# Adapted from: https://djangosnippets.org/snippets/2593/
class LargeTablePaginator(Paginator):
    """ Overrides the count method to get an estimate instead of actual count
    when not filtered
    """

    def _get_estimate(self):
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT reltuples FROM pg_class WHERE relname = %s",
                           [self.object_list.query.model._meta.db_table])
            return int(cursor.fetchone()[0])
        except:
            return 0

    def _get_count(self):
        """
        Changed to use an estimate if the estimate is greater than 10,000
        Returns the total number of objects, across all pages.
        """
        if not hasattr(self, "_count") or self._count is None:
            try:
                estimate = 0
                if not self.object_list.query.where:
                    estimate = self._get_estimate()
                if estimate < 10000:
                    self._count = self.object_list.count()
                else:
                    self._count = estimate
            except (AttributeError, TypeError):
                # AttributeError if object_list has no count() method.
                # TypeError if object_list.count() requires arguments
                # (i.e. is of type list).
                self._count = len(self.object_list)
        return self._count
    count = property(_get_count)


@admin.register(Ping)
class PingsAdmin(admin.ModelAdmin):
    search_fields = ("owner__name", "owner__code", "owner__user__email")
    readonly_fields = ("owner", )
    list_select_related = ("owner", "owner__user")
    list_display = ("id", "created", "owner", "email", "scheme", "method",
                    "ua")
    list_filter = ("created", SchemeListFilter, MethodListFilter,
                   "start", "fail")

    paginator = LargeTablePaginator

    def email(self, obj):
        return obj.owner.user.email if obj.owner.user else None


@admin.register(Channel)
class ChannelsAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('css/admin/channels.css',)
        }

    search_fields = ["value", "user__email"]
    list_select_related = ("user", )
    list_display = ("id", "name", "email", "formatted_kind", "value",
                    "num_notifications")
    list_filter = ("kind", )
    raw_id_fields = ("user", "checks", )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(Count("notification", distinct=True))

        return qs

    def email(self, obj):
        return obj.user.email if obj.user else None

    @mark_safe
    def formatted_kind(self, obj):
        if obj.kind == "email" and not obj.email_verified:
            return "Email <i>(unconfirmed)</i>"

        return obj.get_kind_display()

    formatted_kind.short_description = "Kind"

    def num_notifications(self, obj):
        return obj.notification__count

    num_notifications.short_description = "# Notifications"


@admin.register(Notification)
class NotificationsAdmin(admin.ModelAdmin):
    search_fields = ["owner__name", "owner__code", "channel__value"]
    list_select_related = ("owner", "channel")
    list_display = ("id", "created", "check_status", "owner",
                    "channel_kind", "channel_value")
    list_filter = ("created", "check_status", "channel__kind")

    def channel_kind(self, obj):
        return obj.channel.kind

    def channel_value(self, obj):
        return obj.channel.value


@admin.register(Flip)
class FlipsAdmin(admin.ModelAdmin):
    list_display = ("id", "created", "processed", "owner", "old_status",
                    "new_status")
    raw_id_fields = ("owner", )
