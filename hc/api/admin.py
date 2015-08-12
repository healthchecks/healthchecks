from django.contrib import admin

from hc.api.models import Channel, Check, Ping


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

    list_display = ("id", "name", "created", "code", "status", "email",
                    "last_ping")
    list_select_related = ("user", )
    actions = ["send_alert"]

    list_filter = ("status", OwnershipListFilter)

    def email(self, obj):
        return obj.user.email if obj.user else None

    def send_alert(self, request, qs):
        for check in qs:
            check.send_alert()

        self.message_user(request, "%d alert(s) sent" % qs.count())

    send_alert.short_description = "Send Alert"


@admin.register(Ping)
class PingsAdmin(admin.ModelAdmin):
    list_select_related = ("owner", )
    list_display = ("id", "created", "check_name", "email", "scheme", "method",
                    "ua")

    def check_name(self, obj):
        return obj.owner.name if obj.owner.name else obj.owner.code

    def email(self, obj):
        return obj.owner.user.email if obj.owner.user else None


@admin.register(Channel)
class ChannelsAdmin(admin.ModelAdmin):
    list_select_related = ("user", )
    list_display = ("id", "code", "user", "kind", "value")
