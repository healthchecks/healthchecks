from django.contrib import admin

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

    search_fields = ["name", "user__email"]
    list_display = ("id", "name", "created", "code", "status", "email",
                    "last_ping")
    list_select_related = ("user", )
    list_filter = ("status", OwnershipListFilter, "last_ping")
    actions = ["send_alert"]


    def email(self, obj):
        return obj.user.email if obj.user else None

    def send_alert(self, request, qs):
        for check in qs:
            check.send_alert()

        self.message_user(request, "%d alert(s) sent" % qs.count())

    send_alert.short_description = "Send Alert"


@admin.register(Ping)
class PingsAdmin(admin.ModelAdmin):
    search_fields = ("owner__name", "owner__code", "owner__user__email")
    list_select_related = ("owner", )
    list_display = ("id", "created", "check_name", "email", "scheme", "method",
                    "ua")
    list_filter = ("created", "scheme", "method")

    def check_name(self, obj):
        return obj.owner.name if obj.owner.name else obj.owner.code

    def email(self, obj):
        return obj.owner.user.email if obj.owner.user else None


@admin.register(Channel)
class ChannelsAdmin(admin.ModelAdmin):
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
                    "channel_kind", "channel_value", "status")
    list_filter = ("created", "check_status", "channel__kind")

    def check_name(self, obj):
        return obj.owner.name_then_code()

    def channel_kind(self, obj):
        return obj.channel.kind

    def channel_value(self, obj):
        return obj.channel.value
