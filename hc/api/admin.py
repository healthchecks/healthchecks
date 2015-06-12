from django.contrib import admin

from hc.api.models import Check

@admin.register(Check)
class ChecksAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "user", "last_ping")
