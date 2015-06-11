from django.contrib import admin

from hc.checks.models import Canary


@admin.register(Canary)
class CanaryAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "user", "last_ping")
