from django.contrib import admin

from hc.api.models import Check


@admin.register(Check)
class ChecksAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "user", "last_ping")
    actions = ["send_alert"]

    def send_alert(self, request, qs):
        for check in qs:
            check.send_alert()

        self.message_user(request, "%d alert(s) sent" % qs.count())

    send_alert.short_description = "Send Alert"
