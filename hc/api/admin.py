from django.contrib import admin
from django.core.paginator import Paginator
from django.db import connection
from hc.api.models import Channel, Check, Notification, Ping


class OwnershipListFilter(admin.SimpleListFilter):
    title = "Ownership"
    parameter_name = 'ownership'

    def lookups(self, request, model_admin):
        return (
            ('assigned', "Assigned"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'assigned':
            return queryset.filter(user__isnull=False)
        return queryset


@admin.register(Check)
class ChecksAdmin(admin.ModelAdmin):

    class Media:
        css = {
            'all': ('css/admin/checks.css',)
        }

    search_fields = ["name", "user__email", "code"]
    list_display = ("id", "name_tags", "created", "code", "status", "email",
                    "last_ping", "n_pings")
    list_select_related = ("user", )
    list_filter = ("status", OwnershipListFilter, "last_ping")
    actions = ["send_alert"]

    def email(self, obj):
        return obj.user.email if obj.user else None

    def name_tags(self, obj):
        if not obj.tags:
            return obj.name

        return "%s [%s]" % (obj.name, obj.tags)

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
        if self._count is None:
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
    list_select_related = ("owner", "owner__user")
    list_display = ("id", "created", "check_name", "email", "scheme", "method",
                    "ua")
    list_filter = ("created", SchemeListFilter, MethodListFilter)
    paginator = LargeTablePaginator

    def check_name(self, obj):
        return obj.owner.name if obj.owner.name else obj.owner.code

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
    list_display = ("id", "code", "email", "formatted_kind", "value",
                    "num_notifications")
    list_filter = ("kind", )

    def email(self, obj):
        return obj.user.email if obj.user else None

    def formatted_kind(self, obj):
        if obj.kind == "pd":
            return "PagerDuty"
        elif obj.kind == "victorops":
            return "VictorOps"
        elif obj.kind == "pushbullet":
            return "Pushbullet"
        elif obj.kind == "po":
            return "Pushover"
        elif obj.kind == "webhook":
            return "Webhook"
        elif obj.kind == "slack":
            return "Slack"
        elif obj.kind == "hipchat":
            return "HipChat"
        elif obj.kind == "email" and obj.email_verified:
            return "Email"
        elif obj.kind == "email" and not obj.email_verified:
            return "Email <i>(unverified)</i>"
        else:
            raise NotImplementedError("Bad channel kind: %s" % obj.kind)

    formatted_kind.short_description = "Kind"
    formatted_kind.allow_tags = True

    def num_notifications(self, obj):
        return Notification.objects.filter(channel=obj).count()

    num_notifications.short_description = "# Notifications"


@admin.register(Notification)
class NotificationsAdmin(admin.ModelAdmin):
    search_fields = ["owner__name", "owner__code", "channel__value"]
    list_select_related = ("owner", "channel")
    list_display = ("id", "created", "check_status", "check_name",
                    "channel_kind", "channel_value")
    list_filter = ("created", "check_status", "channel__kind")

    def check_name(self, obj):
        return obj.owner.name_then_code()

    def channel_kind(self, obj):
        return obj.channel.kind

    def channel_value(self, obj):
        return obj.channel.value
