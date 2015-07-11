from django.contrib import admin

from hc.api.models import Check


@admin.register(Check)
class ChecksAdmin(admin.ModelAdmin):
    class Media:
        css = {
         'all': ('css/admin/checks.css',)
        }

    list_display = ("id", "name", "created", "code", "status", "email", "last_ping")
    list_select_related = ("user", )
    actions = ["send_alert"]

    def email(self, obj):
        return obj.user.email if obj.user else None

    def send_alert(self, request, qs):
        for check in qs:
            check.send_alert()

        self.message_user(request, "%d alert(s) sent" % qs.count())

    send_alert.short_description = "Send Alert"
